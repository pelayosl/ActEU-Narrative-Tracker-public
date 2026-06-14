import uuid
from datetime import datetime, timezone

from app.exceptions import (
    ClassifierNotFound,
    NoPendingPipeline,
    PendingPipelineMismatch,
    ProjectAccessDenied,
    ProjectNotFound,
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.classification import (
    ClassifierMetadata,
    DocumentProxy,
    LabellingResult,
    ProxyLabel,
)
from app.schemas.project import PendingPipeline, Project
from app.schemas.topic import Topic


class ProjectService:
    """CRUD only — never dispatches tasks."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        topic_repo: TopicRepository,
    ) -> None:
        self._project_repo = project_repo
        self._topic_repo = topic_repo

    async def create_project(self, owner_id: str, name: str) -> Project:
        project = Project(
            project_id=str(uuid.uuid4()),
            owner_id=owner_id,
            name=name,
            created_at=datetime.now(timezone.utc),
        )
        await self._project_repo.save(project)
        return project

    async def get_project(self, project_id: str) -> Project:
        project = await self._project_repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFound
        return project

    async def list_projects(self, owner_id: str) -> list[Project]:
        return await self._project_repo.find_by_owner(owner_id)

    async def delete_project(self, project_id: str) -> None:
        await self._project_repo.delete(project_id)

    async def save_classifier(self, project_id: str, classifier: ClassifierMetadata) -> None:
        await self._project_repo.add_classifier(project_id, classifier)

    async def get_classifier(self, project_id: str, classifier_id: str) -> ClassifierMetadata:
        classifier = await self._project_repo.find_classifier(project_id, classifier_id)
        if classifier is None:
            raise ClassifierNotFound
        return classifier

    async def get_available_topics(self, project_id: str) -> list[Topic]:
        """Returns the 3 core topics plus all topics across the project's classifiers."""
        core_topics = await self._topic_repo.find_all()
        classifiers = await self._project_repo.find_all_classifiers(project_id)

        seen = {t.topic_id for t in core_topics}
        subtopics = [
            topic
            for classifier in classifiers
            for topic in classifier.topics
            if topic.topic_id not in seen and not seen.add(topic.topic_id)
        ]
        return core_topics + subtopics

    async def verify_project_owner(self, project_id: str, user_id: str) -> None:
        """Raises ProjectNotFound or ProjectAccessDenied if the user does not own the project."""
        project = await self._project_repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFound
        if project.owner_id != user_id:
            raise ProjectAccessDenied

    async def filter_proxies_by_subtopics(
        self,
        project_id: str,
        subtopics: list[str],
        confidence_threshold: float | None = None,
    ) -> dict[str, list[str]]:
        """Returns a mapping of doc_id → matching subtopic names for every project proxy
        carrying at least one of the requested subtopic labels. When `confidence_threshold`
        is set, labels whose confidence is below it (or `None`) are excluded."""
        return await self._project_repo.filter_proxy_doc_ids_by_subtopics(
            project_id, subtopics, confidence_threshold
        )

    async def get_proxy_confidence_by_topics(
        self,
        project_id: str,
        topics: list[str]
    ) -> dict[str, dict[str, float]]:
        """Maps each requested topic to a {doc_id: confidence} map drawn from the project's
        proxies. Used by the visualiser to resolve project-scoped subtopics (both for
        matching documents and for their relevance). Topics with no proxy matches are
        omitted."""
        if not topics:
            return {}
        return await self._project_repo.find_proxy_confidence_by_topics(project_id, topics)

    async def upsert_document_proxies(self, project_id: str, proxies: list[DocumentProxy]) -> None:
        await self._project_repo.upsert_document_proxies(project_id, proxies)

    async def set_pending_pipeline(self, project_id: str, pipeline: PendingPipeline) -> None:
        await self._project_repo.set_pending_pipeline(project_id, pipeline)

    async def stamp_pipeline_classifier(self, project_id: str, classifier_id: str) -> None:
        """Stamp the trained classifier's ID onto the pending pipeline.
        Called by ClassifierTrainingTask after save_classifier succeeds, so that
        apply_pipeline_labels can verify the pipeline still belongs to this classifier."""
        await self._project_repo.stamp_pipeline_classifier(project_id, classifier_id)

    async def update_reconciled_topics(
        self, project_id: str, reconciled_topics: list[Topic]
    ) -> None:
        await self._project_repo.update_reconciled_topics(project_id, reconciled_topics)

    async def clear_pending_pipeline(self, project_id: str) -> None:
        await self._project_repo.clear_pending_pipeline(project_id)

    async def get_pending_pipeline(self, project_id: str) -> PendingPipeline | None:
        return await self._project_repo.find_pending_pipeline(project_id)

    async def get_labelled_doc_ids(self, project_id: str, classifier_id: str) -> set[str]:
        """Returns the set of doc_ids already carrying a label from the given classifier."""
        return set(await self._project_repo.find_labelled_doc_ids(project_id, classifier_id))

    async def apply_pipeline_labels(
        self, project_id: str, classifier_id: str
    ) -> LabellingResult:
        """Phase 1 labelling: writes proxies for the documents already in topic_mapping
        using the classifier's topics. Clears the pending pipeline on success.
        Raises NoPendingPipeline if no pipeline is present, ClassifierNotFound if the
        classifier does not belong to the project, PendingPipelineMismatch if the
        pipeline was overwritten by a newer run and no longer belongs to this
        classifier (in which case the pipeline is NOT cleared)."""
        pipeline = await self._project_repo.find_pending_pipeline(project_id)
        if pipeline is None:
            raise NoPendingPipeline

        classifier = await self._project_repo.find_classifier(project_id, classifier_id)
        if classifier is None:
            raise ClassifierNotFound

        # Verify the pending pipeline still belongs to this classifier.
        # classifier_id is stamped onto the pipeline by ClassifierTrainingTask.
        # None means training hasn't completed yet, or a new run overwrote the pipeline.
        # Either way, Phase 1 is not available for a classifier when pipeline classifier ID is "None".
        if pipeline.classifier_id != classifier_id:
            raise PendingPipelineMismatch

        topic_mapping = pipeline.topic_mapping

        # Build (doc_id → list[ProxyLabel]) by walking the classifier's topics and unioning
        # doc_ids from their origin_topic_ids.
        doc_to_labels: dict[str, list[ProxyLabel]] = {}
        topic_summary: dict[str, int] = {}

        for topic in classifier.topics:
            source_ids = topic.origin_topic_ids if topic.origin_topic_ids else [topic.topic_id]
            doc_ids_for_topic: set[str] = set()
            for sid in source_ids:
                doc_ids_for_topic.update(topic_mapping.get(sid, []))

            if not doc_ids_for_topic:
                continue

            label = ProxyLabel(
                topic_id=topic.topic_id,
                name=topic.name,
                description=topic.description,
                classifier_id=classifier_id,
                confidence=1,
            )
            for doc_id in doc_ids_for_topic:
                doc_to_labels.setdefault(doc_id, []).append(label)

            topic_summary[topic.topic_id] = len(doc_ids_for_topic)

        proxies = [
            DocumentProxy(doc_id=doc_id, labels=labels)
            for doc_id, labels in doc_to_labels.items()
        ]

        if proxies:
            await self._project_repo.upsert_document_proxies(project_id, proxies)

        await self._project_repo.clear_pending_pipeline(project_id)

        return LabellingResult(
            project_id=project_id,
            total_labelled=len(proxies),
            topic_summary=topic_summary,
        )
