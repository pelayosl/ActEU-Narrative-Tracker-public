from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.schemas.search import SearchQuery


class DocumentRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["documents"]

    def _build_filter(self, query: SearchQuery) -> dict:
        filters: list[dict] = []

        for keyword in query.keywords:
            if not keyword:
                continue
            regex = {"$regex": keyword, "$options": "i"}
            filters.append({"$or": [{"headline": regex}, {"plain_text": regex}]})

        if query.date_from or query.date_to:
            date_filter: dict = {}
            if query.date_from:
                date_filter["$gte"] = query.date_from
            if query.date_to:
                date_filter["$lte"] = query.date_to
            filters.append({"published_time": date_filter})

        if query.languages:
            filters.append({"language": {"$in": query.languages}})

        if query.platforms:
            filters.append({"platform": {"$in": query.platforms}})

        if query.topics:
            filters.append({"acteu_topic.label": {"$in": query.topics}})

        # if query.subtopics: This will be useful if the project export functionality is implemented, but not yet.
        #     filters.append({
        #         "$or": [
        #             {"subtopics.topic_id": {"$in": query.subtopics}},
        #             {"subtopics.label": {"$in": query.subtopics}},
        #         ]
        #     })

        if not filters:
            return {}
        return {"$and": filters}

    def _coerce_object_ids(self, doc_ids: list[str]) -> list[ObjectId]:
        object_ids: list[ObjectId] = []
        for doc_id in doc_ids:
            try:
                object_ids.append(ObjectId(doc_id))
            except (InvalidId, TypeError):
                continue
        return object_ids

    async def find(self, query: SearchQuery) -> list[dict]:
        query_filter = self._build_filter(query)
        cursor = self._collection.find(query_filter).sort("published_time", -1).limit(
            settings.DOCUMENT_SEARCH_LIMIT
        )
        return [doc async for doc in cursor]

    async def find_by_ids(self, doc_ids: list[str]) -> list[dict]:
        object_ids = self._coerce_object_ids(doc_ids)
        if not object_ids:
            return []
        cursor = self._collection.find({"_id": {"$in": object_ids}})
        return [doc async for doc in cursor]

    async def count(self, query: SearchQuery) -> int:
        query_filter = self._build_filter(query)
        return await self._collection.count_documents(query_filter)

    async def get_excerpt(self, doc_id: str) -> str:
        try:
            object_id = ObjectId(doc_id)
        except (InvalidId, TypeError):
            return ""

        doc = await self._collection.find_one({"_id": object_id}, {"plain_text": 1})
        plain_text = (doc or {}).get("plain_text", "")
        plain_text = plain_text.strip()
        if len(plain_text) > 250:
            return f"{plain_text[:250].rstrip()}..."
        return plain_text
