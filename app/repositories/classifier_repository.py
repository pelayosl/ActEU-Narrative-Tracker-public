from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.classification import ClassifierMetadata


class ClassifierRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["classifiers"]

    async def save_classifier(self, metadata: ClassifierMetadata) -> None:
        raise NotImplementedError

    async def find_by_user(self, user_id: str) -> list[ClassifierMetadata]:
        raise NotImplementedError

    async def find_by_id(self, classifier_id: str) -> ClassifierMetadata:
        raise NotImplementedError

    async def delete_classifier(self, classifier_id: str) -> None:
        raise NotImplementedError
