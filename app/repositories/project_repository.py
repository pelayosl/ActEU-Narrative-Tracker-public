from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.project import Project


class ProjectRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["projects"]

    async def save(self, project: Project) -> None:
        raise NotImplementedError

    async def find_by_id(self, project_id: str) -> Project | None:
        raise NotImplementedError

    async def find_by_owner(self, owner_id: str) -> list[Project]:
        raise NotImplementedError

    async def delete(self, project_id: str) -> None:
        raise NotImplementedError

    async def add_classifier(self, project_id: str, classifier: ClassifierMetadata) -> None:
        raise NotImplementedError

    async def find_classifier(self, project_id: str, classifier_id: str) -> ClassifierMetadata | None:
        raise NotImplementedError

    async def find_all_classifiers(self, project_id: str) -> list[ClassifierMetadata]:
        raise NotImplementedError

    async def upsert_document_proxies(self, project_id: str, proxies: list[DocumentProxy]) -> None:
        raise NotImplementedError
