from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.topic import Topic


class TopicRepository:
    """Read-only — the topics collection is static (3 core topics, seeded once)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["topics"]

    async def find_all(self) -> list[Topic]:
        raise NotImplementedError

    async def find_by_core_topic(self, core_topic: str) -> list[Topic]:
        raise NotImplementedError
