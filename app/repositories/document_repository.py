from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.search import SearchQuery


class DocumentRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["documents"]

    async def find(self, query: SearchQuery) -> list[dict]:
        raise NotImplementedError

    async def find_by_ids(self, doc_ids: list[str]) -> list[dict]:
        raise NotImplementedError

    async def count(self, query: SearchQuery) -> int:
        raise NotImplementedError

    async def get_excerpt(self, doc_id: str) -> str:
        raise NotImplementedError
