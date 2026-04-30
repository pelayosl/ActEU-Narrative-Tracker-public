
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.project import Project
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
