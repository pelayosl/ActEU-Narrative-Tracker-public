from datetime import datetime, timezone

from app.repositories.topic_repository import TopicRepository


async def test_find_all_returns_core_and_subtopics_with_core_topic(db):
    """find_all surfaces both core topics (core_topic = slug) and db subtopics
    (core_topic = None), so the service can split them for the search form."""
    await db.topics.insert_many([
        {
            "topic_id": "core-1",
            "name": "Immigration",
            "description": "",
            "core_topic": "immigration",
            "created_at": datetime.now(timezone.utc),
        },
        {
            "topic_id": "sub-1",
            "name": "Asylum policy",
            "description": "",
            "core_topic": None,
            "created_at": datetime.now(timezone.utc),
        },
    ])

    topics = await TopicRepository(db).find_all()

    by_id = {t.topic_id: t for t in topics}
    assert by_id["core-1"].core_topic == "immigration"
    assert by_id["sub-1"].core_topic is None


async def test_find_all_empty(db):
    assert await TopicRepository(db).find_all() == []
