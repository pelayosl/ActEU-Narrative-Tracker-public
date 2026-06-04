from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.schemas.visualisation import Dashboard, VisualisationQuery
from app.services.visualisation_service import VisualisationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def document_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.topic_presence_over_time.return_value = []
    repo.topic_presence_by_language.return_value = []
    repo.topic_presence_by_platform.return_value = []
    repo.entities_for_topic.return_value = []
    repo.relevant_documents.return_value = []
    return repo


@pytest.fixture
def project_service() -> AsyncMock:
    service = AsyncMock()
    service.get_proxy_doc_ids_by_topics.return_value = {}
    return service


@pytest.fixture
def service(document_repo, project_service) -> VisualisationService:
    return VisualisationService(document_repo, project_service)


def make_query(**overrides) -> VisualisationQuery:
    base = {
        "topics": ["immigration"],
        "date_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "date_to": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "languages": [],
        "platforms": [],
    }
    base.update(overrides)
    return VisualisationQuery(**base)


# ---------------------------------------------------------------------------
# load_dashboard()
# ---------------------------------------------------------------------------

class TestLoadDashboard:
    async def test_returns_dashboard(self, service):
        result = await service.load_dashboard(make_query())
        assert isinstance(result, Dashboard)

    async def test_empty_repo_results_yield_empty_relevant_documents(self, service):
        result = await service.load_dashboard(make_query())
        assert result.relevant_documents == []

    async def test_no_project_skips_proxy_resolution(self, service, project_service):
        await service.load_dashboard(make_query(), project_id=None)
        project_service.get_proxy_doc_ids_by_topics.assert_not_called()

    async def test_project_resolves_proxies(self, service, project_service):
        await service.load_dashboard(make_query(topics=["sub-a"]), project_id="p1")
        project_service.get_proxy_doc_ids_by_topics.assert_awaited_once_with("p1", ["sub-a"])

    async def test_proxy_doc_ids_forwarded_to_repo(self, service, document_repo, project_service):
        project_service.get_proxy_doc_ids_by_topics.return_value = {"immigration": ["a", "b"]}

        await service.load_dashboard(make_query(), project_id="p1")

        # proxy_doc_ids for the topic is the 6th positional arg
        _, kwargs = document_repo.topic_presence_over_time.call_args
        args = document_repo.topic_presence_over_time.call_args.args
        assert args[0] == "immigration"
        assert args[5] == ["a", "b"]

    async def test_topic_without_proxy_match_passes_none(self, service, document_repo):
        await service.load_dashboard(make_query(), project_id="p1")
        args = document_repo.topic_presence_over_time.call_args.args
        assert args[5] is None


# ---------------------------------------------------------------------------
# topic_evolution
# ---------------------------------------------------------------------------

class TestTopicEvolution:
    async def test_maps_points_per_topic(self, service, document_repo):
        document_repo.topic_presence_over_time.return_value = [
            {"date": "2024-05-07", "count": 500},
            {"date": "2024-07-10", "count": 4},
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))

        assert len(result.topic_evolution) == 1
        ts = result.topic_evolution[0]
        assert ts.topic == "immigration"
        assert ts.series[0].date == "2024-05-07"
        assert ts.series[0].count == 500
        assert ts.series[1].count == 4

    async def test_one_series_per_topic(self, service, document_repo):
        result = await service.load_dashboard(make_query(topics=["a", "b", "c"]))
        assert [ts.topic for ts in result.topic_evolution] == ["a", "b", "c"]
        assert document_repo.topic_presence_over_time.await_count == 3

    async def test_empty_topics_yields_empty_evolution(self, service):
        result = await service.load_dashboard(make_query(topics=[]))
        assert result.topic_evolution == []


# ---------------------------------------------------------------------------
# topics_by_language
# ---------------------------------------------------------------------------

class TestTopicsByLanguage:
    async def test_maps_counts_per_topic(self, service, document_repo):
        document_repo.topic_presence_by_language.return_value = [
            {"language": "es", "count": 1000},
            {"language": "fi", "count": 100},
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))

        assert len(result.topics_by_language) == 1
        breakdown = result.topics_by_language[0]
        assert breakdown.topic == "immigration"
        assert breakdown.counts[0].language == "es"
        assert breakdown.counts[0].count == 1000
        assert breakdown.counts[1].language == "fi"

    async def test_query_params_forwarded(self, service, document_repo):
        query = make_query(topics=["immigration"], languages=["es"], platforms=["twitter"])
        await service.load_dashboard(query)

        args = document_repo.topic_presence_by_language.call_args.args
        assert args[0] == "immigration"
        assert args[1] == query.date_from
        assert args[2] == query.date_to
        assert args[3] == ["es"]
        assert args[4] == ["twitter"]


# ---------------------------------------------------------------------------
# topics_by_platform
# ---------------------------------------------------------------------------

class TestTopicsByPlatform:
    async def test_maps_counts_per_topic(self, service, document_repo):
        document_repo.topic_presence_by_platform.return_value = [
            {"platform": "twitter", "count": 800},
            {"platform": "telegram", "count": 50},
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))

        assert len(result.topics_by_platform) == 1
        breakdown = result.topics_by_platform[0]
        assert breakdown.topic == "immigration"
        assert breakdown.counts[0].platform == "twitter"
        assert breakdown.counts[0].count == 800
        assert breakdown.counts[1].platform == "telegram"

    async def test_one_breakdown_per_topic(self, service, document_repo):
        result = await service.load_dashboard(make_query(topics=["a", "b"]))
        assert [b.topic for b in result.topics_by_platform] == ["a", "b"]
        assert document_repo.topic_presence_by_platform.await_count == 2

    async def test_proxy_doc_ids_forwarded(self, service, document_repo, project_service):
        project_service.get_proxy_doc_ids_by_topics.return_value = {"immigration": ["a", "b"]}
        await service.load_dashboard(make_query(), project_id="p1")
        args = document_repo.topic_presence_by_platform.call_args.args
        assert args[5] == ["a", "b"]


# ---------------------------------------------------------------------------
# top_entities (PageRank)
# ---------------------------------------------------------------------------

class TestTopEntities:
    async def test_ranks_entities_per_topic(self, service, document_repo):
        document_repo.entities_for_topic.return_value = [
            ["Spain", "EU"],
            ["Spain", "EU"],
            ["Spain", "Lampedusa"],
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))

        assert len(result.top_entities) == 1
        topic_entities = result.top_entities[0]
        assert topic_entities.topic == "immigration"
        names = [e.entity for e in topic_entities.entities]
        assert "Spain" in names
        # scores are floats and present
        assert all(isinstance(e.score, float) for e in topic_entities.entities)

    async def test_caps_at_five_entities(self, service, document_repo):
        document_repo.entities_for_topic.return_value = [
            ["A", "B", "C", "D", "E", "F", "G"],
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))
        assert len(result.top_entities[0].entities) == 5

    async def test_empty_entities_yields_empty_list(self, service, document_repo):
        document_repo.entities_for_topic.return_value = []
        result = await service.load_dashboard(make_query(topics=["immigration"]))
        assert result.top_entities[0].entities == []

    async def test_one_entry_per_topic(self, service, document_repo):
        result = await service.load_dashboard(make_query(topics=["a", "b", "c"]))
        assert [te.topic for te in result.top_entities] == ["a", "b", "c"]
        assert document_repo.entities_for_topic.await_count == 3

    async def test_proxy_doc_ids_forwarded(self, service, document_repo, project_service):
        project_service.get_proxy_doc_ids_by_topics.return_value = {"immigration": ["a", "b"]}
        await service.load_dashboard(make_query(), project_id="p1")
        args = document_repo.entities_for_topic.call_args.args
        assert args[5] == ["a", "b"]


# ---------------------------------------------------------------------------
# relevant_documents
# ---------------------------------------------------------------------------

def make_relevant(doc_id, relevance, **overrides):
    base = {
        "doc_id": doc_id,
        "platform": "twitter",
        "language": "es",
        "published_time": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "plain_text": "Some content.",
        "relevance": relevance,
    }
    base.update(overrides)
    return base


class TestRelevantDocuments:
    async def test_maps_repo_fields_to_preview(self, service, document_repo):
        document_repo.relevant_documents.return_value = [
            make_relevant("d1", 0.9, platform="telegram", language="de"),
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))

        assert len(result.relevant_documents) == 1
        rd = result.relevant_documents[0]
        assert rd.doc_id == "d1"
        assert rd.platform == "telegram"
        assert rd.language == "de"
        assert rd.topic == "immigration"
        assert rd.relevance_score == 0.9

    async def test_none_relevance_becomes_zero(self, service, document_repo):
        document_repo.relevant_documents.return_value = [make_relevant("d1", None)]
        result = await service.load_dashboard(make_query(topics=["sub"]))
        assert result.relevant_documents[0].relevance_score == 0.0

    async def test_merged_and_sorted_across_topics(self, service, document_repo):
        def per_topic(topic, *args, **kwargs):
            return {
                "a": [make_relevant("d1", 0.4)],
                "b": [make_relevant("d2", 0.95)],
            }[topic]
        document_repo.relevant_documents.side_effect = per_topic

        result = await service.load_dashboard(make_query(topics=["a", "b"]))
        ids = [r.doc_id for r in result.relevant_documents]
        assert ids == ["d2", "d1"]

    async def test_dedup_keeps_highest_relevance(self, service, document_repo):
        def per_topic(topic, *args, **kwargs):
            # same doc matched by two topics with different confidence
            return {
                "a": [make_relevant("d1", 0.3)],
                "b": [make_relevant("d1", 0.8)],
            }[topic]
        document_repo.relevant_documents.side_effect = per_topic

        result = await service.load_dashboard(make_query(topics=["a", "b"]))
        assert len(result.relevant_documents) == 1
        assert result.relevant_documents[0].relevance_score == 0.8

    async def test_capped_at_ten(self, service, document_repo):
        document_repo.relevant_documents.return_value = [
            make_relevant(f"d{i}", 0.5 + i / 100) for i in range(15)
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))
        assert len(result.relevant_documents) == 10

    async def test_long_excerpt_truncated_to_250(self, service, document_repo):
        document_repo.relevant_documents.return_value = [
            make_relevant("d1", 0.9, plain_text="A" * 400)
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))
        excerpt = result.relevant_documents[0].excerpt
        assert excerpt.endswith("...")
        assert len(excerpt) <= 253

    async def test_proxy_doc_ids_forwarded(self, service, document_repo, project_service):
        project_service.get_proxy_doc_ids_by_topics.return_value = {"immigration": ["a", "b"]}
        await service.load_dashboard(make_query(), project_id="p1")
        args = document_repo.relevant_documents.call_args.args
        assert args[5] == ["a", "b"]
