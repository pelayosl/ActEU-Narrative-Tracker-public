import os
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
from app.schemas.search import SearchTopics, TopicChoice
from app.schemas.topic import Topic


class ProjectService:
    """CRUD for projects, classifiers, document proxies and pipeline state.

    This service never dispatches tasks. It is the only owner of project persistence,
    so tasks reach project storage through it rather than through the repositories.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        topic_repo: TopicRepository,
    ) -> None:
        """Store the repositories this service reads from and writes to.

        :param project_repo: Repository for the projects collection.
        :param topic_repo: Repository for the native topics collection, used to compose
            available-topic facets.
        """
        self._project_repo = project_repo
        self._topic_repo = topic_repo

    async def create_project(self, owner_id: str, name: str) -> Project:
        """Create and persist a new, empty project owned by a user.

        :param owner_id: The owning user's ``user_id``.
        :param name: The project name.
        :returns: The newly created :class:`Project`.
        """
        project = Project(
            project_id=str(uuid.uuid4()),
            owner_id=owner_id,
            name=name,
            created_at=datetime.now(timezone.utc),
        )
        await self._project_repo.save(project)
        return project

    async def get_project(self, project_id: str) -> Project:
        """Fetch a project by id.

        :param project_id: The project to fetch.
        :returns: The matching :class:`Project`.
        :raises ProjectNotFound: If no project has that id.
        """
        project = await self._project_repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFound
        return project

    async def list_projects(self, owner_id: str) -> list[Project]:
        """List every project owned by a user.

        :param owner_id: The owning user's ``user_id``.
        :returns: The user's projects (possibly empty).
        """
        return await self._project_repo.find_by_owner(owner_id)

    async def delete_project(self, project_id: str) -> None:
        """Delete a project and all of its embedded data.

        :param project_id: The project to delete.
        """
        await self._project_repo.delete(project_id)

    async def save_classifier(self, project_id: str, classifier: ClassifierMetadata) -> None:
        """Embed a trained classifier in a project.

        :param project_id: The target project.
        :param classifier: The classifier metadata to store.
        """
        await self._project_repo.add_classifier(project_id, classifier)

    async def get_classifier(self, project_id: str, classifier_id: str) -> ClassifierMetadata:
        """Fetch a single classifier embedded in a project.

        :param project_id: The project that owns the classifier.
        :param classifier_id: The classifier to fetch.
        :returns: The matching :class:`ClassifierMetadata`.
        :raises ClassifierNotFound: If the classifier is absent.
        """
        classifier = await self._project_repo.find_classifier(project_id, classifier_id)
        if classifier is None:
            raise ClassifierNotFound
        return classifier

    async def delete_classifier(self, project_id: str, classifier_id: str) -> None:
        """Delete a classifier and cascade-remove what it produced.

        Removes the ``.bin`` model file, the embedded metadata, and the document-proxy
        labels it produced.

        :param project_id: The project that owns the classifier.
        :param classifier_id: The classifier to delete.
        :raises ClassifierNotFound: If the classifier is absent.
        """
        classifier = await self._project_repo.find_classifier(project_id, classifier_id)
        if classifier is None:
            raise ClassifierNotFound
        try:
            os.remove(classifier.file_path)
        except OSError:
            pass
        await self._project_repo.delete_classifier(project_id, classifier_id)

    async def get_available_topics(self, project_id: str) -> SearchTopics:
        """Compose the search-form topic facets, sourced entirely from the database.

        Core ACTEU topics and db-native subtopics come from the topics collection
        (split by ``core_topic``: a slug marks a core topic, ``None`` marks a subtopic),
        and the project's classifier subtopics are merged into the subtopics, winning on
        a name collision. Core topics submit their slug, subtopics submit their topic_id.

        :param project_id: The project whose classifier subtopics are merged in.
        :returns: A :class:`SearchTopics` with core topics and subtopics.
        """
        native = await self._topic_repo.find_all()

        core_topics = [
            TopicChoice(value=t.core_topic, label=t.name)
            for t in native
            if t.core_topic is not None
        ]

        subtopics: dict[str, str] = {
            t.topic_id: t.name 
            for t in native 
            if t.core_topic is None
        }
        classifiers = await self._project_repo.find_all_classifiers(project_id)
        for classifier in classifiers:
            for topic in classifier.topics:  # project labels win on collision
                subtopics[topic.topic_id] = topic.name

        return SearchTopics(
            core_topics=core_topics,
            subtopics=[
                TopicChoice(value=tid, label=name)
                for tid, name in sorted(subtopics.items(), key=lambda kv: kv[1].lower())
            ],
        )

    async def verify_project_owner(self, project_id: str, user_id: str) -> None:
        """Assert that a user owns a project, called by project-scoped routes.

        :param project_id: The project to check.
        :param user_id: The user expected to own it.
        :raises ProjectNotFound: If the project does not exist.
        :raises ProjectAccessDenied: If the user does not own the project.
        """
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
        """Resolve project subtopics to the proxy documents that carry them.

        Returns a mapping of doc_id → matching subtopic names for every project proxy
        carrying at least one of the requested subtopic labels. When
        ``confidence_threshold`` is set, labels whose confidence is below it (or
        ``None``) are excluded.

        :param project_id: The project whose proxies are inspected.
        :param subtopics: The requested subtopic ``topic_id`` values.
        :param confidence_threshold: Optional minimum label confidence.
        :returns: A ``{doc_id: [subtopic_name, ...]}`` map.
        """
        return await self._project_repo.filter_proxy_doc_ids_by_subtopics(
            project_id, subtopics, confidence_threshold
        )

    async def get_proxy_confidence_by_topics(
        self,
        project_id: str,
        topics: list[str]
    ) -> dict[str, dict[str, float]]:
        """Resolve project subtopics to their proxy documents and confidences.

        Maps each requested topic to a {doc_id: confidence} map drawn from the project's
        proxies, used by the visualiser to resolve project-scoped subtopics both for
        matching documents and for their relevance. Topics with no proxy matches are
        omitted.

        :param project_id: The project whose proxies are inspected.
        :param topics: The requested topic ``topic_id`` values.
        :returns: A ``{topic_id: {doc_id: confidence}}`` map (empty when no topics).
        """
        if not topics:
            return {}
        return await self._project_repo.find_proxy_confidence_by_topics(project_id, topics)

    async def upsert_document_proxies(self, project_id: str, proxies: list[DocumentProxy]) -> None:
        """Insert or extend document proxies in a project, idempotently.

        :param project_id: The target project.
        :param proxies: The document proxies (with labels) to upsert.
        """
        await self._project_repo.upsert_document_proxies(project_id, proxies)

    async def set_pending_pipeline(self, project_id: str, pipeline: PendingPipeline) -> None:
        """Store a pending pipeline on a project, overwriting any existing one.

        :param project_id: The target project.
        :param pipeline: The pending pipeline state to persist.
        """
        await self._project_repo.set_pending_pipeline(project_id, pipeline)

    async def stamp_pipeline_classifier(self, project_id: str, classifier_id: str) -> None:
        """Stamp the trained classifier's id onto the pending pipeline.

        Called by ``ClassifierTrainingTask`` after ``save_classifier`` succeeds, so that
        ``apply_pipeline_labels`` can verify the pipeline still belongs to this
        classifier.

        :param project_id: The target project.
        :param classifier_id: The trained classifier's id.
        """
        await self._project_repo.stamp_pipeline_classifier(project_id, classifier_id)

    async def update_reconciled_topics(
        self, project_id: str, reconciled_topics: list[Topic]
    ) -> None:
        """Update only the reconciled topics of the pending pipeline.

        :param project_id: The target project.
        :param reconciled_topics: The reconciled topics to store.
        """
        await self._project_repo.update_reconciled_topics(project_id, reconciled_topics)

    async def clear_pending_pipeline(self, project_id: str) -> None:
        """Clear a project's pending pipeline, called after Phase 1 labelling.

        :param project_id: The target project.
        """
        await self._project_repo.clear_pending_pipeline(project_id)

    async def get_pending_pipeline(self, project_id: str) -> PendingPipeline | None:
        """Read a project's current pending pipeline.

        :param project_id: The project to read.
        :returns: The :class:`PendingPipeline`, or ``None`` if none is active.
        """
        return await self._project_repo.find_pending_pipeline(project_id)

    async def get_labelled_doc_ids(self, project_id: str, classifier_id: str) -> set[str]:
        """Return the doc_ids already labelled by a classifier, used by Phase 2.

        :param project_id: The project whose proxies are inspected.
        :param classifier_id: The classifier whose labels are matched.
        :returns: The set of doc_ids carrying a label from this classifier.
        """
        return set(await self._project_repo.find_labelled_doc_ids(project_id, classifier_id))

    async def apply_pipeline_labels(
        self, project_id: str, classifier_id: str
    ) -> LabellingResult:
        """Apply Phase 1 labels from the training-era topic mapping.

        Writes proxies (confidence 1) for the documents already in ``topic_mapping``
        using the classifier's topics, then clears the pending pipeline on success.
        Performs no ML inference and never writes to the core documents collection.

        :param project_id: The project to label.
        :param classifier_id: The classifier whose topics drive the labelling.
        :returns: A :class:`LabellingResult` summarising the labels written.
        :raises NoPendingPipeline: If no pending pipeline is present.
        :raises ClassifierNotFound: If the classifier does not belong to the project.
        :raises PendingPipelineMismatch: If a newer run overwrote the pipeline so it no
            longer belongs to this classifier, in which case the pipeline is not cleared.
        """
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
