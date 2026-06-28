from pymongo.asynchronous.database import AsyncDatabase

from app.schemas.topic import Topic


class TopicRepository:
    """Read-only data-access layer for the ``topics`` collection.

    The collection holds the 3 core ACTEU topics and the db-native subtopics,
    catalogued at ingestion. It is never written to at runtime by the pipeline, so
    this repository exposes lookups only.
    """

    def __init__(self, db: AsyncDatabase) -> None:
        """Bind the repository to the ``topics`` collection of the given database.

        :param db: The async MongoDB database handle.
        """
        self._collection = db["topics"]

    async def find_by_id(self, topic_id: str) -> Topic | None:
        """Look up a single topic by its ``topic_id``.

        :param topic_id: The topic identifier (UUID for subtopics).
        :returns: The matching :class:`Topic`, or ``None`` if not found.
        """
        doc = await self._collection.find_one({"topic_id": topic_id})
        if doc:
            return Topic(**doc)
        return None

    async def find_all(self) -> list[Topic]:
        """Return every native topic in the collection.

        All native topics: the 3 core topics (core_topic = slug) and the db subtopics
        (core_topic = None). Project subtopics live in projects, not here.

        :returns: A list of all :class:`Topic` documents.
        """
        cursor = self._collection.find()
        return [Topic(**doc) async for doc in cursor]

