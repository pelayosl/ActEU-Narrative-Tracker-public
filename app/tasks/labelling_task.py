import asyncio

from app.exceptions import LabellingLocked
from app.infrastructure.classifier_wrapper import ClassifierWrapper
from app.tasks.task_context import (
    mutex_manager_context,
    project_service_context,
    search_service_context,
)
from app.schemas.classification import DocumentProxy, LabellingResult, ProxyLabel
from app.schemas.search import SearchQuery
from app.schemas.topic import OTHER_TOPIC_ID
from app.tasks.celery_app import celery_app


def _lock_key(project_id: str) -> str:
    return f"labelling:project:{project_id}"


@celery_app.task
def labelling_task(project_id: str, classifier_id: str, query: dict) -> dict:
    """Phase 2 labelling: runs a new search, applies the trained classifier, persists proxies.
    Depends on: ClassifierWrapper, MutexManager, SearchService, ProjectService."""
    return asyncio.run(_run(project_id, classifier_id, query))


async def _run(project_id: str, classifier_id: str, query: dict) -> dict:
    search_query = SearchQuery(**query)
    key = _lock_key(project_id)

    async with mutex_manager_context() as mutex:
        if not await mutex.acquire(key):
            raise LabellingLocked(
                f"Another labelling job is already running for project {project_id}"
            )

        try:
            return (await _label(project_id, classifier_id, search_query)).model_dump()
        finally:
            await mutex.release(key)


async def _label(
    project_id: str, classifier_id: str, query: SearchQuery
) -> LabellingResult:
    # Load classifier metadata (topics + file_path)
    async with project_service_context() as project_service:
        classifier = await project_service.get_classifier(project_id, classifier_id)
        already_labelled = await project_service.get_labelled_doc_ids(project_id, classifier_id)

    # Load FastText model
    wrapper = ClassifierWrapper()
    wrapper.load(classifier.file_path)

    # Run the new query
    async with search_service_context() as search_service:
        search_result = await search_service.search(query)
        candidate_ids = [
            doc.doc_id for doc in search_result.retrieved_docs
            if doc.doc_id not in already_labelled
        ]

        if not candidate_ids:
            return LabellingResult(
                project_id=project_id, total_labelled=0, topic_summary={}
            )

        docs = await search_service.get_documents_by_ids(candidate_ids)

    # Topic lookup: topic_id → (name, description)
    topic_lookup = {t.topic_id: t for t in classifier.topics}

    proxies: list[DocumentProxy] = []
    topic_summary: dict[str, int] = {}

    for doc in docs:
        text = (doc.get("plain_text") or "").strip()
        if not text:
            continue

        topic_id, confidence = wrapper.predict(text)
        if topic_id == OTHER_TOPIC_ID:
            # Document stays unlabelled
            continue
        topic = topic_lookup.get(topic_id)
        if topic is None:
            # Predicted label that doesn't match any classifier topic — skip defensively
            continue

        label = ProxyLabel(
            topic_id=topic.topic_id,
            name=topic.name,
            description=topic.description,
            classifier_id=classifier_id,
            confidence=confidence,
        )
        proxies.append(DocumentProxy(doc_id=str(doc["_id"]), labels=[label]))
        topic_summary[topic_id] = topic_summary.get(topic_id, 0) + 1

    if proxies:
        async with project_service_context() as project_service:
            await project_service.upsert_document_proxies(project_id, proxies)

    return LabellingResult(
        project_id=project_id,
        total_labelled=len(proxies),
        topic_summary=topic_summary,
    )
