from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.topic import Topic


class TopicRepository:

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["topics"]

    async def find_by_id(self, topic_id: str) -> Topic | None:
        doc = await self._collection.find_one({"topic_id": topic_id})
        if doc:
            return Topic(**doc)
        return None

    async def find_all(self) -> list[Topic]:
        cursor = self._collection.find()
        return [Topic(**doc) async for doc in cursor]

    async def find_by_core_topic(self, core_topic: str) -> list[Topic]:
        cursor = self._collection.find({"core_topic": core_topic})
        return [Topic(**doc) async for doc in cursor]
