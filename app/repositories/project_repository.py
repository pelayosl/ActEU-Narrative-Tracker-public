from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.project import Project


class ProjectRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["projects"]

    async def save(self, project: Project) -> None:
        # upsert por project_id
        await self._collection.update_one(
            {"project_id": project.project_id},
            {"$set": project.dict()},
            upsert=True
        )

    async def find_by_id(self, project_id: str) -> Project | None:
        doc = await self._collection.find_one({"project_id": project_id})
        if doc:
            return Project.parse_obj(doc)
        return None

    async def find_by_owner(self, owner_id: str) -> list[Project]:
        cursor = self._collection.find({"owner_id": owner_id})
        return [Project.parse_obj(doc) async for doc in cursor]

    async def delete(self, project_id: str) -> None:
        await self._collection.delete_one({"project_id": project_id})

    async def add_classifier(self, project_id: str, classifier: ClassifierMetadata) -> None:
        # Añade un clasificador al array classifiers
        await self._collection.update_one(
            {"project_id": project_id},
            {"$push": {"classifiers": classifier.dict()}}
        )

    async def find_classifier(self, project_id: str, classifier_id: str) -> ClassifierMetadata | None:
        doc = await self._collection.find_one(
            {"project_id": project_id, "classifiers.classifier_id": classifier_id},
            {"classifiers.$": 1}
        )
        if doc and "classifiers" in doc and doc["classifiers"]:
            return ClassifierMetadata.parse_obj(doc["classifiers"][0])
        return None

    async def find_all_classifiers(self, project_id: str) -> list[ClassifierMetadata]:
        doc = await self._collection.find_one({"project_id": project_id}, {"classifiers": 1})
        if doc and "classifiers" in doc:
            return [ClassifierMetadata.parse_obj(c) for c in doc["classifiers"]]
        return []

    async def upsert_document_proxies(self, project_id: str, proxies: list[DocumentProxy]) -> None:
        # Reemplaza todos los proxies de documentos del proyecto
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": {"document_proxies": [p.dict() for p in proxies]}}
        )
