
from pydantic import BaseModel
from pymongo.asynchronous.database import AsyncDatabase

from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.project import PendingPipeline, Project
from app.schemas.topic import Topic
from pymongo import UpdateOne


class ProjectRepository:
    """Data-access layer for the ``projects`` collection.

    A project document embeds its classifiers, document proxies and pending pipeline,
    so this repository covers all CRUD for those nested structures as well as the
    project itself. Used only by ``ProjectService``.
    """

    def __init__(self, db: AsyncDatabase) -> None:
        """Bind the repository to the ``projects`` collection of the given database.

        :param db: The async MongoDB database handle.
        """
        self._collection = db["projects"]

    async def save(self, project: Project) -> None:
        """Insert or update a project, upserting by ``project_id``.

        :param project: The project entity to persist.
        """
        # upsert por project_id
        await self._collection.update_one(
            {"project_id": project.project_id},
            {"$set": project.model_dump()},
            upsert=True
        )

    async def find_by_id(self, project_id: str) -> Project | None:
        """Look up a single project by its ``project_id``.

        :param project_id: The project identifier (UUID).
        :returns: The matching :class:`Project`, or ``None`` if not found.
        """
        doc = await self._collection.find_one({"project_id": project_id})
        if doc:
            return Project.model_validate(doc)
        return None

    async def find_by_owner(self, owner_id: str) -> list[Project]:
        """Return every project owned by a given user.

        :param owner_id: The owning user's ``user_id``.
        :returns: A list of the user's :class:`Project` entities (possibly empty).
        """
        cursor = self._collection.find({"owner_id": owner_id})
        return [Project.model_validate(doc) async for doc in cursor]

    async def delete(self, project_id: str) -> None:
        """Delete a project and all of its embedded data.

        :param project_id: The project to remove.
        """
        await self._collection.delete_one({"project_id": project_id})

    async def add_classifier(self, project_id: str, classifier: ClassifierMetadata) -> None:
        """Append a trained classifier to the project's ``classifiers`` array.

        :param project_id: The target project.
        :param classifier: The classifier metadata to embed.
        """
        await self._collection.update_one(
            {"project_id": project_id},
            {"$push": {"classifiers": classifier.model_dump()}}
        )

    async def find_classifier(self, project_id: str, classifier_id: str) -> ClassifierMetadata | None:
        """Look up a single embedded classifier within a project.

        :param project_id: The project that owns the classifier.
        :param classifier_id: The classifier identifier (UUID).
        :returns: The matching :class:`ClassifierMetadata`, or ``None`` if absent.
        """
        doc = await self._collection.find_one(
            {"project_id": project_id, "classifiers.classifier_id": classifier_id},
            {"classifiers.$": 1}
        )
        if doc and "classifiers" in doc and doc["classifiers"]:
            return ClassifierMetadata.model_validate(doc["classifiers"][0])
        return None

    async def find_all_classifiers(self, project_id: str) -> list[ClassifierMetadata]:
        """Return every classifier embedded in a project.

        :param project_id: The project to read.
        :returns: A list of :class:`ClassifierMetadata` (empty if the project has none
            or does not exist).
        """
        doc = await self._collection.find_one({"project_id": project_id}, {"classifiers": 1})
        if doc and "classifiers" in doc:
            return [ClassifierMetadata.model_validate(c) for c in doc["classifiers"]]
        return []

    async def delete_classifier(self, project_id: str, classifier_id: str) -> None:
        """Remove a classifier and cascade-delete the labels it produced.

        Removes the classifier and every document-proxy label it produced, then drops
        any proxy left with no labels. Mirrors the full cascade of project deletion.

        :param project_id: The project that owns the classifier.
        :param classifier_id: The classifier to remove.
        """
        await self._collection.update_one(
            {"project_id": project_id},
            {
                "$pull": {
                    "classifiers": {"classifier_id": classifier_id},
                    "document_proxies.$[].labels": {"classifier_id": classifier_id},
                }
            },
        )
        # Second pass: prune proxies whose labels are now empty.
        await self._collection.update_one(
            {"project_id": project_id},
            {"$pull": {"document_proxies": {"labels": {"$size": 0}}}},
        )

    async def filter_proxy_doc_ids_by_subtopics(
        self,
        project_id: str,
        subtopics: list[str],
        confidence_threshold: float | None = None,
    ) -> dict[str, list[str]]:
        """Resolve project subtopics to the proxy documents that carry them.

        Returns a mapping of doc_id → matching subtopic names for every project proxy
        that carries at least one of the requested subtopic labels. When
        `confidence_threshold` is set, labels whose confidence is below it (or `None`)
        are excluded.

        :param project_id: The project whose proxies are inspected.
        :param subtopics: The requested subtopic ``topic_id`` values.
        :param confidence_threshold: Optional minimum label confidence; ``None``
            disables filtering.
        :returns: A ``{doc_id: [subtopic_name, ...]}`` map (empty if no project or no
            matches).
        """
        doc = await self._collection.find_one(
            {"project_id": project_id},
            {"document_proxies": 1}
        )
        if not doc:
            return {}
        subtopics_set = set(subtopics)

        def label_matches(label: dict) -> bool:
            if label["topic_id"] not in subtopics_set:
                return False
            if confidence_threshold is None:
                return True
            confidence = label.get("confidence")
            return confidence is not None and confidence >= confidence_threshold

        result: dict[str, list[str]] = {}
        for proxy in doc.get("document_proxies", []):
            matching_names = [
                label["name"]
                for label in proxy.get("labels", [])
                if label_matches(label)
            ]
            if matching_names:
                result[proxy["doc_id"]] = matching_names
        return result

    async def find_proxy_confidence_by_topics(
        self,
        project_id: str,
        topics: list[str],
    ) -> dict[str, dict[str, float]]:
        """Resolve project subtopics to their proxy documents and confidences.

        Maps each requested topic_id to a {doc_id: confidence} map drawn from the
        project's document proxies. A topic_id appears at most once per proxy (it is a
        unique UUID, and labelling guards against duplicate (topic_id, classifier_id)
        labels), so each doc contributes a single confidence. Topics with no proxy
        matches are omitted from the result.

        :param project_id: The project whose proxies are inspected.
        :param topics: The requested topic ``topic_id`` values.
        :returns: A ``{topic_id: {doc_id: confidence}}`` map (empty if no project).
        """
        doc = await self._collection.find_one(
            {"project_id": project_id},
            {"document_proxies": 1},
        )
        if not doc:
            return {}
        topics_set = set(topics)
        result: dict[str, dict[str, float]] = {}
        for proxy in doc.get("document_proxies", []):
            for label in proxy.get("labels", []):
                topic_id = label.get("topic_id")
                confidence = label.get("confidence")
                if topic_id not in topics_set or confidence is None:
                    continue
                result.setdefault(topic_id, {})[proxy["doc_id"]] = confidence
        return result

    async def set_pending_pipeline(self, project_id: str, pipeline: PendingPipeline) -> None:
        """Store a pending pipeline on the project, overwriting any existing one.

        Overwriting resets ``classifier_id`` to ``null`` for the new pipeline.

        :param project_id: The target project.
        :param pipeline: The pending pipeline state to persist.
        """
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"pending_pipeline": pipeline.model_dump()}},
        )

    async def stamp_pipeline_classifier(self, project_id: str, classifier_id: str) -> None:
        """Record which classifier the current pending pipeline belongs to.

        Called after training so Phase 1 labelling can validate that the pipeline has
        not been overwritten by a newer run.

        :param project_id: The target project.
        :param classifier_id: The trained classifier's identifier.
        """
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"pending_pipeline.classifier_id": classifier_id}},
        )

    async def update_reconciled_topics(
        self, project_id: str, reconciled_topics: list[Topic]
    ) -> None:
        """Update only the ``reconciled_topics`` of the pending pipeline.

        ``generated_topics`` and ``topic_mapping`` are left unchanged.

        :param project_id: The target project.
        :param reconciled_topics: The reconciled topics to store.
        """
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"pending_pipeline.reconciled_topics": [t.model_dump() for t in reconciled_topics]}},
        )

    async def clear_pending_pipeline(self, project_id: str) -> None:
        """Clear the project's pending pipeline (set it to ``None``).

        Called after Phase 1 labelling completes successfully.

        :param project_id: The target project.
        """
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"pending_pipeline": None}},
        )

    async def find_pending_pipeline(self, project_id: str) -> PendingPipeline | None:
        """Read the project's current pending pipeline.

        :param project_id: The project to read.
        :returns: The :class:`PendingPipeline`, or ``None`` if none is active.
        """
        doc = await self._collection.find_one(
            {"project_id": project_id}, {"pending_pipeline": 1}
        )
        if doc and doc.get("pending_pipeline"):
            return PendingPipeline.model_validate(doc["pending_pipeline"])
        return None

    async def find_labelled_doc_ids(self, project_id: str, classifier_id: str) -> list[str]:
        """Return doc_ids already labelled by a given classifier in this project.

        Used by Phase 2 labelling to pre-filter candidates that are already labelled.

        :param project_id: The project whose proxies are inspected.
        :param classifier_id: The classifier whose labels are matched.
        :returns: The list of doc_ids carrying a label from this classifier.
        """
        doc = await self._collection.find_one(
            {"project_id": project_id},
            {"document_proxies": 1},
        )
        if not doc:
            return []
        return [
            proxy["doc_id"]
            for proxy in doc.get("document_proxies", [])
            if any(label.get("classifier_id") == classifier_id for label in proxy.get("labels", []))
        ]

    async def upsert_document_proxies(self, project_id: str, proxies: list[DocumentProxy]) -> None:
        """Insert or extend document proxies in the project, idempotently.

        For each proxy, the proxy is pushed if its ``doc_id`` is not yet present;
        otherwise each label is appended only if a label with the same
        ``(topic_id, classifier_id)`` does not already exist. This makes repeated
        labelling runs safe to re-apply.

        :param project_id: The target project.
        :param proxies: The document proxies (with labels) to upsert.
        """
        operations = []
        for proxy in proxies:

            # Case 1: doc_id doesn't exist
            operations.append(UpdateOne(
                {
                    "project_id": project_id,
                    "document_proxies.doc_id": {"$ne": proxy.doc_id}
                },
                {"$push": {"document_proxies": proxy.model_dump()}},
            ))

            # Case 2: doc_id exists
            for label in proxy.labels:
                operations.append(UpdateOne(
                    {
                        "project_id": project_id,
                        "document_proxies.doc_id": proxy.doc_id,
                        "document_proxies.labels": {
                            "$not": {
                                "$elemMatch": {
                                    "topic_id": label.topic_id,
                                    "classifier_id": label.classifier_id
                                }
                            }
                        }
                    },
                    {"$push": {"document_proxies.$.labels": label.model_dump()}},
                ))
        if operations:
            await self._collection.bulk_write(operations, ordered=False)
