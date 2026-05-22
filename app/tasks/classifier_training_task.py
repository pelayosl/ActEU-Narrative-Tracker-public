import asyncio
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.infrastructure.classifier_wrapper import ClassifierWrapper
from app.tasks.task_context import project_service_context, search_service_context
from app.schemas.classification import ClassifierMetadata
from app.schemas.topic import Topic
from app.tasks.celery_app import celery_app


@celery_app.task
def classifier_training_task(
    topics: list[dict], project_id: str, name: str
) -> dict:
    """Train a FastText classifier on the validated topics.
    Depends on: ClassifierWrapper, SearchService (fetch texts), ProjectService (save classifier)."""
    return asyncio.run(_run(topics, project_id, name))


async def _run(topics: list[dict], project_id: str, name: str) -> dict:
    validated_topics = [Topic(**t) for t in topics]

    # Retrieve topic_id → doc_ids mapping from the project's pending pipeline
    async with project_service_context() as project_service:
        pipeline = await project_service.get_pending_pipeline(project_id)

    if pipeline is None:
        raise ValueError("No pending pipeline found — topic generation must run first")

    topic_mapping = pipeline.topic_mapping

    # Build training data: for each validated topic, union doc_ids from its origin topics.
    # origin_topic_ids are the generation-era UUIDs which are the keys in topic_mapping.
    # If origin_topic_ids is empty (user skipped reconciliation), use the topic's own ID.
    training_pairs: list[tuple[str, str]] = []  # (doc_id, topic_id label for this classifier)
    for topic in validated_topics:
        source_ids = topic.origin_topic_ids if topic.origin_topic_ids else [topic.topic_id]
        doc_ids = []
        for sid in source_ids:
            doc_ids.extend(topic_mapping.get(sid, []))

        for doc_id in doc_ids:
            training_pairs.append((doc_id, topic.topic_id))

    if not training_pairs:
        raise ValueError("No training data found — topic mapping is empty or doc_ids are missing")

    all_doc_ids = list({doc_id for doc_id, _ in training_pairs})

    async with search_service_context() as search_service:
        docs = await search_service.get_documents_by_ids(all_doc_ids)

    # Build doc_id → text lookup
    doc_texts: dict[str, str] = {
        str(doc["_id"]): (doc.get("plain_text") or "").strip()
        for doc in docs
    }

    texts: list[str] = []
    labels: list[str] = []
    for doc_id, topic_id in training_pairs:
        text = doc_texts.get(doc_id, "")
        if text:
            texts.append(text)
            labels.append(topic_id)

    if not texts:
        raise ValueError("All documents had empty text — cannot train classifier")

    classifier_id = str(uuid.uuid4())
    file_path = f"{settings.CLASSIFIER_DIR}/{classifier_id}.bin"

    wrapper = ClassifierWrapper()
    wrapper.train(texts, labels)
    wrapper.save(file_path)

    metadata = ClassifierMetadata(
        classifier_id=classifier_id,
        name=name,
        topics=validated_topics,
        file_path=file_path,
        created_at=datetime.now(timezone.utc),
    )

    async with project_service_context() as project_service:
        await project_service.save_classifier(project_id, metadata)

    return metadata.model_dump()
