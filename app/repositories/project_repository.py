
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.project import PendingPipeline, Project
from app.schemas.topic import Topic
from pymongo import UpdateOne


class ProjectRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["projects"]

    async def save(self, project: Project) -> None:
        # upsert por project_id
        await self._collection.update_one(
            {"project_id": project.project_id},
            {"$set": project.model_dump()},
            upsert=True
        )

    async def find_by_id(self, project_id: str) -> Project | None:
        doc = await self._collection.find_one({"project_id": project_id})
        if doc:
            return Project.model_validate(doc)
        return None

    async def find_by_owner(self, owner_id: str) -> list[Project]:
        cursor = self._collection.find({"owner_id": owner_id})
        return [Project.model_validate(doc) async for doc in cursor]

    async def delete(self, project_id: str) -> None:
        await self._collection.delete_one({"project_id": project_id})

    async def add_classifier(self, project_id: str, classifier: ClassifierMetadata) -> None:
        await self._collection.update_one(
            {"project_id": project_id},
            {"$push": {"classifiers": classifier.model_dump()}}
        )

    async def find_classifier(self, project_id: str, classifier_id: str) -> ClassifierMetadata | None:
        doc = await self._collection.find_one(
            {"project_id": project_id, "classifiers.classifier_id": classifier_id},
            {"classifiers.$": 1}
        )
        if doc and "classifiers" in doc and doc["classifiers"]:
            return ClassifierMetadata.model_validate(doc["classifiers"][0])
        return None

    async def find_all_classifiers(self, project_id: str) -> list[ClassifierMetadata]:
        doc = await self._collection.find_one({"project_id": project_id}, {"classifiers": 1})
        if doc and "classifiers" in doc:
            return [ClassifierMetadata.model_validate(c) for c in doc["classifiers"]]
        return []

    async def filter_proxy_doc_ids_by_subtopics(
        self,
        project_id: str,
        doc_ids: list[str],
        subtopics: list[str],
        confidence_threshold: float | None = None,
    ) -> list[str]:
        doc = await self._collection.find_one(
            {"project_id": project_id},
            {"document_proxies": 1}
        )
        if not doc:
            return []
        doc_ids_set = set(doc_ids)
        subtopics_set = set(subtopics)

        def label_matches(label: dict) -> bool:
            if label["topic_id"] not in subtopics_set:
                return False
            if confidence_threshold is None:
                return True
            confidence = label.get("confidence")
            return confidence is not None and confidence >= confidence_threshold

        return [
            proxy["doc_id"]
            for proxy in doc.get("document_proxies", [])
            if proxy["doc_id"] in doc_ids_set
            and any(label_matches(label) for label in proxy.get("labels", []))
        ]

    async def find_proxy_doc_ids_by_topics(
        self,
        project_id: str,
        topics: list[str],
    ) -> dict[str, list[str]]:
        """Maps each requested topic to the list of doc_ids whose project proxies carry a
        label for it. A label matches when its `topic_id` or `name` equals the topic.
        Topics with no proxy matches are omitted from the result."""
        doc = await self._collection.find_one(
            {"project_id": project_id},
            {"document_proxies": 1},
        )
        if not doc:
            return {}
        topics_set = set(topics)
        result: dict[str, list[str]] = {}
        for proxy in doc.get("document_proxies", []):
            for label in proxy.get("labels", []):
                for key in (label.get("topic_id"), label.get("name")):
                    if key in topics_set:
                        result.setdefault(key, []).append(proxy["doc_id"])
        return result

    async def set_pending_pipeline(self, project_id: str, pipeline: PendingPipeline) -> None:
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"pending_pipeline": pipeline.model_dump()}},
        )

    async def update_reconciled_topics(
        self, project_id: str, reconciled_topics: list[Topic]
    ) -> None:
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"pending_pipeline.reconciled_topics": [t.model_dump() for t in reconciled_topics]}},
        )

    async def clear_pending_pipeline(self, project_id: str) -> None:
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"pending_pipeline": None}},
        )

    async def find_pending_pipeline(self, project_id: str) -> PendingPipeline | None:
        doc = await self._collection.find_one(
            {"project_id": project_id}, {"pending_pipeline": 1}
        )
        if doc and doc.get("pending_pipeline"):
            return PendingPipeline.model_validate(doc["pending_pipeline"])
        return None

    async def find_labelled_doc_ids(self, project_id: str, classifier_id: str) -> list[str]:
        """Returns doc_ids in this project whose proxies already carry a label from the given classifier."""
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
