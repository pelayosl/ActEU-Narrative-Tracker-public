from datetime import datetime, timezone

import pytest

from app.repositories.document_repository import DocumentRepository


def make_doc(**overrides) -> dict:
    base = {
        "headline": "Headline",
        "plain_text": "Plain text content.",
        "platform": "twitter",
        "language": "es",
        "published_time": datetime(2024, 5, 7, 12, 0, 0, tzinfo=timezone.utc),
        "acteu_topic": {"label": "immigration", "confidence": 0.8},
        "subtopics": [],
        "named_entities": [],
        "sentiment": "neutral",
    }
    base.update(overrides)
    return base


@pytest.fixture
async def repo(db):
    return DocumentRepository(db)


D_FROM = datetime(2024, 1, 1, tzinfo=timezone.utc)
D_TO = datetime(2024, 12, 31, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# topic_presence_over_time()
# ---------------------------------------------------------------------------

class TestTopicPresenceOverTime:
    async def test_groups_by_day(self, db, repo):
        await db["documents"].insert_many([
            make_doc(published_time=datetime(2024, 5, 7, 9, tzinfo=timezone.utc)),
            make_doc(published_time=datetime(2024, 5, 7, 18, tzinfo=timezone.utc)),
            make_doc(published_time=datetime(2024, 7, 10, 10, tzinfo=timezone.utc)),
        ])
        result = await repo.topic_presence_over_time("immigration", D_FROM, D_TO, [], [])
        assert result == [
            {"date": "2024-05-07", "count": 2},
            {"date": "2024-07-10", "count": 1},
        ]

    async def test_only_counts_matching_topic(self, db, repo):
        await db["documents"].insert_many([
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.9}),
            make_doc(acteu_topic={"label": "climate_change", "confidence": 0.9}),
        ])
        result = await repo.topic_presence_over_time("immigration", D_FROM, D_TO, [], [])
        assert result == [{"date": "2024-05-07", "count": 1}]

    async def test_matches_db_subtopic(self, db, repo):
        await db["documents"].insert_one(make_doc(
            acteu_topic={"label": "climate_change", "confidence": 0.9},
            subtopics=[{"topic_id": "t1", "label": "wind_energy", "confidence": 0.7}],
        ))
        result = await repo.topic_presence_over_time("wind_energy", D_FROM, D_TO, [], [])
        assert result == [{"date": "2024-05-07", "count": 1}]

    async def test_matches_proxy_doc_ids(self, db, repo):
        res = await db["documents"].insert_one(make_doc(
            acteu_topic={"label": "other", "confidence": 0.9},
        ))
        proxy_id = str(res.inserted_id)
        # No core/subtopic match, only the proxy id resolves it.
        result = await repo.topic_presence_over_time(
            "project_sub", D_FROM, D_TO, [], [], proxy_doc_ids=[proxy_id]
        )
        assert result == [{"date": "2024-05-07", "count": 1}]

    async def test_dedups_across_sources(self, db, repo):
        """A doc matching both by core topic and by proxy id is counted once."""
        res = await db["documents"].insert_one(make_doc(
            acteu_topic={"label": "immigration", "confidence": 0.9},
        ))
        proxy_id = str(res.inserted_id)
        result = await repo.topic_presence_over_time(
            "immigration", D_FROM, D_TO, [], [], proxy_doc_ids=[proxy_id]
        )
        assert result == [{"date": "2024-05-07", "count": 1}]

    async def test_date_range_excludes_outside(self, db, repo):
        await db["documents"].insert_many([
            make_doc(published_time=datetime(2023, 1, 1, tzinfo=timezone.utc)),
            make_doc(published_time=datetime(2024, 5, 7, tzinfo=timezone.utc)),
        ])
        result = await repo.topic_presence_over_time("immigration", D_FROM, D_TO, [], [])
        assert result == [{"date": "2024-05-07", "count": 1}]

    async def test_language_filter(self, db, repo):
        await db["documents"].insert_many([
            make_doc(language="es"),
            make_doc(language="fi"),
        ])
        result = await repo.topic_presence_over_time("immigration", D_FROM, D_TO, ["fi"], [])
        assert result == [{"date": "2024-05-07", "count": 1}]

    async def test_platform_filter(self, db, repo):
        await db["documents"].insert_many([
            make_doc(platform="twitter"),
            make_doc(platform="telegram"),
        ])
        result = await repo.topic_presence_over_time("immigration", D_FROM, D_TO, [], ["telegram"])
        assert result == [{"date": "2024-05-07", "count": 1}]

    async def test_no_match_returns_empty(self, db, repo):
        await db["documents"].insert_one(make_doc())
        result = await repo.topic_presence_over_time("nonexistent", D_FROM, D_TO, [], [])
        assert result == []


# ---------------------------------------------------------------------------
# topic_presence_by_language()
# ---------------------------------------------------------------------------

class TestTopicPresenceByLanguage:
    async def test_groups_by_language(self, db, repo):
        await db["documents"].insert_many([
            make_doc(language="es"),
            make_doc(language="es"),
            make_doc(language="fi"),
        ])
        result = await repo.topic_presence_by_language("immigration", D_FROM, D_TO, [], [])
        assert result == [
            {"language": "es", "count": 2},
            {"language": "fi", "count": 1},
        ]

    async def test_only_counts_matching_topic(self, db, repo):
        await db["documents"].insert_many([
            make_doc(language="es", acteu_topic={"label": "immigration", "confidence": 0.9}),
            make_doc(language="fi", acteu_topic={"label": "climate_change", "confidence": 0.9}),
        ])
        result = await repo.topic_presence_by_language("immigration", D_FROM, D_TO, [], [])
        assert result == [{"language": "es", "count": 1}]

    async def test_matches_proxy_doc_ids(self, db, repo):
        res = await db["documents"].insert_one(make_doc(
            language="de", acteu_topic={"label": "other", "confidence": 0.9},
        ))
        proxy_id = str(res.inserted_id)
        result = await repo.topic_presence_by_language(
            "project_sub", D_FROM, D_TO, [], [], proxy_doc_ids=[proxy_id]
        )
        assert result == [{"language": "de", "count": 1}]

    async def test_sorted_by_count_descending(self, db, repo):
        await db["documents"].insert_many([
            make_doc(language="fr"),
            make_doc(language="es"),
            make_doc(language="es"),
            make_doc(language="es"),
        ])
        result = await repo.topic_presence_by_language("immigration", D_FROM, D_TO, [], [])
        assert result[0] == {"language": "es", "count": 3}
        assert result[1] == {"language": "fr", "count": 1}

    async def test_no_match_returns_empty(self, db, repo):
        await db["documents"].insert_one(make_doc())
        result = await repo.topic_presence_by_language("nonexistent", D_FROM, D_TO, [], [])
        assert result == []
