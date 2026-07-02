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
        # db subtopics are matched by topic_id (the value the frontend submits), not label.
        result = await repo.topic_presence_over_time("t1", D_FROM, D_TO, [], [])
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


# ---------------------------------------------------------------------------
# topic_presence_by_platform()
# ---------------------------------------------------------------------------

class TestTopicPresenceByPlatform:
    async def test_groups_by_platform(self, db, repo):
        await db["documents"].insert_many([
            make_doc(platform="twitter"),
            make_doc(platform="twitter"),
            make_doc(platform="telegram"),
        ])
        result = await repo.topic_presence_by_platform("immigration", D_FROM, D_TO, [], [])
        assert result == [
            {"platform": "twitter", "count": 2},
            {"platform": "telegram", "count": 1},
        ]

    async def test_only_counts_matching_topic(self, db, repo):
        await db["documents"].insert_many([
            make_doc(platform="twitter", acteu_topic={"label": "immigration", "confidence": 0.9}),
            make_doc(platform="telegram", acteu_topic={"label": "climate_change", "confidence": 0.9}),
        ])
        result = await repo.topic_presence_by_platform("immigration", D_FROM, D_TO, [], [])
        assert result == [{"platform": "twitter", "count": 1}]

    async def test_matches_db_subtopic(self, db, repo):
        await db["documents"].insert_one(make_doc(
            platform="media",
            acteu_topic={"label": "climate_change", "confidence": 0.9},
            subtopics=[{"topic_id": "t1", "label": "wind_energy", "confidence": 0.7}],
        ))
        result = await repo.topic_presence_by_platform("t1", D_FROM, D_TO, [], [])
        assert result == [{"platform": "media", "count": 1}]

    async def test_matches_proxy_doc_ids(self, db, repo):
        res = await db["documents"].insert_one(make_doc(
            platform="telegram", acteu_topic={"label": "other", "confidence": 0.9},
        ))
        proxy_id = str(res.inserted_id)
        result = await repo.topic_presence_by_platform(
            "project_sub", D_FROM, D_TO, [], [], proxy_doc_ids=[proxy_id]
        )
        assert result == [{"platform": "telegram", "count": 1}]

    async def test_dedups_across_sources(self, db, repo):
        res = await db["documents"].insert_one(make_doc(
            platform="twitter", acteu_topic={"label": "immigration", "confidence": 0.9},
        ))
        proxy_id = str(res.inserted_id)
        result = await repo.topic_presence_by_platform(
            "immigration", D_FROM, D_TO, [], [], proxy_doc_ids=[proxy_id]
        )
        assert result == [{"platform": "twitter", "count": 1}]

    async def test_sorted_by_count_descending(self, db, repo):
        await db["documents"].insert_many([
            make_doc(platform="media"),
            make_doc(platform="twitter"),
            make_doc(platform="twitter"),
            make_doc(platform="twitter"),
        ])
        result = await repo.topic_presence_by_platform("immigration", D_FROM, D_TO, [], [])
        assert result[0] == {"platform": "twitter", "count": 3}
        assert result[1] == {"platform": "media", "count": 1}

    async def test_language_filter(self, db, repo):
        await db["documents"].insert_many([
            make_doc(platform="twitter", language="es"),
            make_doc(platform="telegram", language="fi"),
        ])
        result = await repo.topic_presence_by_platform("immigration", D_FROM, D_TO, ["fi"], [])
        assert result == [{"platform": "telegram", "count": 1}]

    async def test_date_range_excludes_outside(self, db, repo):
        await db["documents"].insert_many([
            make_doc(platform="twitter", published_time=datetime(2023, 1, 1, tzinfo=timezone.utc)),
            make_doc(platform="telegram", published_time=datetime(2024, 5, 7, tzinfo=timezone.utc)),
        ])
        result = await repo.topic_presence_by_platform("immigration", D_FROM, D_TO, [], [])
        assert result == [{"platform": "telegram", "count": 1}]

    async def test_no_match_returns_empty(self, db, repo):
        await db["documents"].insert_one(make_doc())
        result = await repo.topic_presence_by_platform("nonexistent", D_FROM, D_TO, [], [])
        assert result == []


# ---------------------------------------------------------------------------
# entities_for_topic()
# ---------------------------------------------------------------------------

class TestEntitiesForTopic:
    async def test_returns_entity_lists_per_doc(self, db, repo):
        await db["documents"].insert_many([
            make_doc(named_entities=[{"text": "Spain"}, {"text": "EU"}]),
            make_doc(named_entities=[{"text": "Lampedusa"}]),
        ])
        result = await repo.entities_for_topic("immigration", D_FROM, D_TO, [], [])
        assert sorted(result, key=len) == [["Lampedusa"], ["Spain", "EU"]]

    async def test_omits_docs_without_entities(self, db, repo):
        await db["documents"].insert_many([
            make_doc(named_entities=[{"text": "Spain"}]),
            make_doc(named_entities=[]),
        ])
        result = await repo.entities_for_topic("immigration", D_FROM, D_TO, [], [])
        assert result == [["Spain"]]

    async def test_only_matching_topic(self, db, repo):
        await db["documents"].insert_many([
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.9},
                     named_entities=[{"text": "Spain"}]),
            make_doc(acteu_topic={"label": "climate_change", "confidence": 0.9},
                     named_entities=[{"text": "COP29"}]),
        ])
        result = await repo.entities_for_topic("immigration", D_FROM, D_TO, [], [])
        assert result == [["Spain"]]

    async def test_matches_proxy_doc_ids(self, db, repo):
        res = await db["documents"].insert_one(make_doc(
            acteu_topic={"label": "other", "confidence": 0.9},
            named_entities=[{"text": "ProjectActor"}],
        ))
        proxy_id = str(res.inserted_id)
        result = await repo.entities_for_topic(
            "project_sub", D_FROM, D_TO, [], [], proxy_doc_ids=[proxy_id]
        )
        assert result == [["ProjectActor"]]

    async def test_language_filter(self, db, repo):
        await db["documents"].insert_many([
            make_doc(language="es", named_entities=[{"text": "Spain"}]),
            make_doc(language="fi", named_entities=[{"text": "Finland"}]),
        ])
        result = await repo.entities_for_topic("immigration", D_FROM, D_TO, ["fi"], [])
        assert result == [["Finland"]]

    async def test_no_match_returns_empty(self, db, repo):
        await db["documents"].insert_one(make_doc(named_entities=[{"text": "Spain"}]))
        result = await repo.entities_for_topic("nonexistent", D_FROM, D_TO, [], [])
        assert result == []


# ---------------------------------------------------------------------------
# relevant_documents()
# ---------------------------------------------------------------------------

class TestRelevantDocuments:
    async def test_core_topic_uses_acteu_confidence(self, db, repo):
        await db["documents"].insert_many([
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.6}),
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.95}),
        ])
        result = await repo.relevant_documents("immigration", D_FROM, D_TO, [], [])
        assert [round(d["relevance"], 2) for d in result] == [0.95, 0.6]

    async def test_sorted_by_relevance_descending(self, db, repo):
        await db["documents"].insert_many([
            make_doc(acteu_topic={"label": "immigration", "confidence": c})
            for c in (0.3, 0.9, 0.5)
        ])
        result = await repo.relevant_documents("immigration", D_FROM, D_TO, [], [])
        scores = [d["relevance"] for d in result]
        assert scores == sorted(scores, reverse=True)

    async def test_limit_is_respected(self, db, repo):
        await db["documents"].insert_many([
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.5})
            for _ in range(15)
        ])
        result = await repo.relevant_documents("immigration", D_FROM, D_TO, [], [], limit=10)
        assert len(result) == 10

    async def test_db_subtopic_uses_subtopic_confidence(self, db, repo):
        await db["documents"].insert_one(make_doc(
            acteu_topic={"label": "climate_change", "confidence": 0.99},
            subtopics=[{"topic_id": "t1", "label": "wind_energy", "confidence": 0.42}],
        ))
        result = await repo.relevant_documents("t1", D_FROM, D_TO, [], [])
        assert len(result) == 1
        # relevance comes from the matched subtopic, not the (higher) core topic
        assert round(result[0]["relevance"], 2) == 0.42

    async def test_proxy_match_uses_proxy_confidence(self, db, repo):
        res = await db["documents"].insert_one(make_doc(
            acteu_topic={"label": "other", "confidence": 0.9},
        ))
        proxy_id = str(res.inserted_id)
        result = await repo.relevant_documents(
            "project_sub", D_FROM, D_TO, [], [], proxy_confidence={proxy_id: 0.75}
        )
        assert len(result) == 1
        assert result[0]["relevance"] == 0.75

    async def test_ranks_by_confidence_across_sources(self, db, repo):
        confident = await db["documents"].insert_one(
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.7})
        )
        proxy_only = await db["documents"].insert_one(
            make_doc(acteu_topic={"label": "other", "confidence": 0.9})
        )
        proxy_id = str(proxy_only.inserted_id)
        # both resolve to "immigration": one by core topic (0.7), one by proxy (0.95)
        result = await repo.relevant_documents(
            "immigration", D_FROM, D_TO, [], [], proxy_confidence={proxy_id: 0.95}
        )
        assert len(result) == 2
        assert result[0]["doc_id"] == proxy_id
        assert result[0]["relevance"] == 0.95
        assert result[1]["doc_id"] == str(confident.inserted_id)
        assert result[1]["relevance"] == 0.7

    async def test_projects_expected_fields(self, db, repo):
        await db["documents"].insert_one(make_doc(
            platform="telegram", language="de",
            acteu_topic={"label": "immigration", "confidence": 0.8},
        ))
        result = await repo.relevant_documents("immigration", D_FROM, D_TO, [], [])
        doc = result[0]
        assert set(doc.keys()) == {
            "doc_id", "platform", "language", "published_time", "plain_text", "relevance"
        }
        assert doc["platform"] == "telegram"
        assert doc["language"] == "de"

    async def test_language_filter(self, db, repo):
        await db["documents"].insert_many([
            make_doc(language="es", acteu_topic={"label": "immigration", "confidence": 0.8}),
            make_doc(language="fi", acteu_topic={"label": "immigration", "confidence": 0.9}),
        ])
        result = await repo.relevant_documents("immigration", D_FROM, D_TO, ["fi"], [])
        assert len(result) == 1
        assert result[0]["language"] == "fi"

    async def test_no_match_returns_empty(self, db, repo):
        await db["documents"].insert_one(make_doc())
        result = await repo.relevant_documents("nonexistent", D_FROM, D_TO, [], [])
        assert result == []

    async def test_keeps_top_documents_of_each_platform(self, db, repo):
        await db["documents"].insert_many([
            make_doc(platform="twitter", acteu_topic={"label": "immigration", "confidence": c})
            for c in (0.9, 0.85, 0.8)
        ])
        await db["documents"].insert_one(
            make_doc(platform="telegram", acteu_topic={"label": "immigration", "confidence": 0.5})
        )
        result = await repo.relevant_documents("immigration", D_FROM, D_TO, [], [], limit=2)
        platforms = {d["platform"] for d in result}
        assert platforms == {"twitter", "telegram"}
        # Two twitter (the limit) + one telegram.
        assert sum(d["platform"] == "twitter" for d in result) == 2
        assert sum(d["platform"] == "telegram" for d in result) == 1


# ---------------------------------------------------------------------------
# mean_topic_confidence()
# ---------------------------------------------------------------------------

class TestMeanTopicConfidence:
    async def test_averages_core_confidence(self, db, repo):
        await db["documents"].insert_many([
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.4}),
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.8}),
        ])
        mean = await repo.mean_topic_confidence("immigration", D_FROM, D_TO, [], [])
        assert round(mean, 2) == 0.6

    async def test_includes_proxy_confidence(self, db, repo):
        # one core match (0.6) and one proxy-only match (0.8) → mean 0.7
        await db["documents"].insert_one(
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.6})
        )
        proxy_only = await db["documents"].insert_one(
            make_doc(acteu_topic={"label": "other", "confidence": 0.9})
        )
        proxy_id = str(proxy_only.inserted_id)
        mean = await repo.mean_topic_confidence(
            "immigration", D_FROM, D_TO, [], [], proxy_confidence={proxy_id: 0.8}
        )
        assert round(mean, 2) == 0.7

    async def test_none_when_no_match(self, db, repo):
        await db["documents"].insert_one(make_doc())
        mean = await repo.mean_topic_confidence("nonexistent", D_FROM, D_TO, [], [])
        assert mean is None


# ---------------------------------------------------------------------------
# count_topic_documents()
# ---------------------------------------------------------------------------

class TestCountTopicDocuments:
    async def test_counts_matching_documents(self, db, repo):
        await db["documents"].insert_many([
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.4}),
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.9}),
            make_doc(acteu_topic={"label": "other", "confidence": 0.9}),
        ])
        count = await repo.count_topic_documents("immigration", D_FROM, D_TO, [], [])
        assert count == 2

    async def test_includes_proxy_documents(self, db, repo):
        await db["documents"].insert_one(
            make_doc(acteu_topic={"label": "immigration", "confidence": 0.6})
        )
        proxy_only = await db["documents"].insert_one(
            make_doc(acteu_topic={"label": "other", "confidence": 0.9})
        )
        proxy_id = str(proxy_only.inserted_id)
        count = await repo.count_topic_documents(
            "immigration", D_FROM, D_TO, [], [], proxy_doc_ids=[proxy_id]
        )
        assert count == 2

    async def test_zero_when_no_match(self, db, repo):
        await db["documents"].insert_one(make_doc())
        count = await repo.count_topic_documents("nonexistent", D_FROM, D_TO, [], [])
        assert count == 0
