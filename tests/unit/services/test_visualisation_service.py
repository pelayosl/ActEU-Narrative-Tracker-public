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
    repo.mean_topic_confidence.return_value = 0.5
    repo.count_topic_documents.return_value = 5
    return repo


@pytest.fixture
def project_service() -> AsyncMock:
    service = AsyncMock()
    service.get_proxy_confidence_by_topics.return_value = {}
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
        project_service.get_proxy_confidence_by_topics.assert_not_called()

    async def test_project_resolves_proxies(self, service, project_service):
        await service.load_dashboard(make_query(topics=["sub-a"]), project_id="p1")
        project_service.get_proxy_confidence_by_topics.assert_awaited_once_with("p1", ["sub-a"])

    async def test_proxy_doc_ids_forwarded_to_repo(self, service, document_repo, project_service):
        project_service.get_proxy_confidence_by_topics.return_value = {"immigration": {"a": 1.0, "b": 1.0}}

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
        project_service.get_proxy_confidence_by_topics.return_value = {"immigration": {"a": 1.0, "b": 1.0}}
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

    async def test_caps_at_ten_entities(self, service, document_repo):
        document_repo.entities_for_topic.return_value = [
            ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"],
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))
        assert len(result.top_entities[0].entities) == 10

    async def test_empty_entities_yields_empty_list(self, service, document_repo):
        document_repo.entities_for_topic.return_value = []
        result = await service.load_dashboard(make_query(topics=["immigration"]))
        assert result.top_entities[0].entities == []

    async def test_one_entry_per_topic(self, service, document_repo):
        result = await service.load_dashboard(make_query(topics=["a", "b", "c"]))
        assert [te.topic for te in result.top_entities] == ["a", "b", "c"]
        assert document_repo.entities_for_topic.await_count == 3

    async def test_proxy_doc_ids_forwarded(self, service, document_repo, project_service):
        project_service.get_proxy_confidence_by_topics.return_value = {"immigration": {"a": 1.0, "b": 1.0}}
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

    async def test_shared_document_appears_under_each_topic(self, service, document_repo):
        def per_topic(topic, *args, **kwargs):
            # the same doc exemplifies both topics, with different confidence
            return {
                "a": [make_relevant("d1", 0.3)],
                "b": [make_relevant("d1", 0.8)],
            }[topic]
        document_repo.relevant_documents.side_effect = per_topic

        result = await service.load_dashboard(make_query(topics=["a", "b"]))
        pairs = [(r.doc_id, r.topic) for r in result.relevant_documents]
        # appears once under each topic, so neither topic is starved
        assert ("d1", "a") in pairs
        assert ("d1", "b") in pairs
        assert len(result.relevant_documents) == 2

    async def test_capped_at_sample_size(self, service, document_repo):
        document_repo.relevant_documents.return_value = [
            make_relevant(f"d{i}", 0.5 + i / 100) for i in range(20)
        ]
        result = await service.load_dashboard(
            make_query(topics=["immigration"], sample_size=12)
        )
        assert len(result.relevant_documents) == 12

    async def test_long_excerpt_truncated_to_250(self, service, document_repo):
        document_repo.relevant_documents.return_value = [
            make_relevant("d1", 0.9, plain_text="A" * 400)
        ]
        result = await service.load_dashboard(make_query(topics=["immigration"]))
        excerpt = result.relevant_documents[0].excerpt
        assert excerpt.endswith("...")
        assert len(excerpt) <= 253

    async def test_proxy_confidence_forwarded(self, service, document_repo, project_service):
        project_service.get_proxy_confidence_by_topics.return_value = {"immigration": {"a": 1.0, "b": 1.0}}
        await service.load_dashboard(make_query(), project_id="p1")
        args = document_repo.relevant_documents.call_args.args
        assert args[5] == {"a": 1.0, "b": 1.0}

    async def test_slots_proportional_to_document_count(self, service, document_repo):
        # Topic "a" matches more documents than "b", so it should contribute more
        # documents to the sample. Each topic owns a distinct, plentiful doc set.
        def count(topic, *args, **kwargs):
            return {"a": 90, "b": 10}[topic]
        document_repo.count_topic_documents.side_effect = count

        def per_topic(topic, *args, **kwargs):
            return [make_relevant(f"{topic}{i}", 0.5) for i in range(10)]
        document_repo.relevant_documents.side_effect = per_topic

        result = await service.load_dashboard(make_query(topics=["a", "b"], sample_size=10))
        topics = [r.topic for r in result.relevant_documents]
        assert len(result.relevant_documents) == 10
        assert topics.count("a") > topics.count("b")

    async def test_empty_topic_still_appears(self, service, document_repo):
        # "b" matches no documents but must still contribute its guaranteed slot.
        def count(topic, *args, **kwargs):
            return {"a": 99, "b": 0}[topic]
        document_repo.count_topic_documents.side_effect = count

        def per_topic(topic, *args, **kwargs):
            return [make_relevant(f"{topic}{i}", 0.5) for i in range(10)]
        document_repo.relevant_documents.side_effect = per_topic

        result = await service.load_dashboard(make_query(topics=["a", "b"], sample_size=10))
        topics = [r.topic for r in result.relevant_documents]
        assert topics.count("b") >= 1

    async def test_selection_varies_platforms_when_available(self, service, document_repo):
        # One topic, 4 slots. The 3 highest-confidence docs are all twitter; a single
        # telegram doc is less confident. Platform interleaving should pull the telegram
        # doc into the selection instead of taking the top 4 twitter docs.
        document_repo.relevant_documents.return_value = [
            make_relevant("t1", 0.9, platform="twitter"),
            make_relevant("t2", 0.85, platform="twitter"),
            make_relevant("t3", 0.8, platform="twitter"),
            make_relevant("t4", 0.75, platform="twitter"),
            make_relevant("g1", 0.5, platform="telegram"),
        ]
        result = await service.load_dashboard(
            make_query(topics=["immigration"], sample_size=4)
        )
        platforms = {r.platform for r in result.relevant_documents}
        ids = {r.doc_id for r in result.relevant_documents}
        assert "telegram" in platforms
        assert "g1" in ids

    async def test_sparse_topic_slots_redistributed(self, service, document_repo):
        # "b" only owns 1 document; its unfilled slots are redistributed to "a" so the
        # sample still reaches sample_size.
        def per_topic(topic, *args, **kwargs):
            if topic == "b":
                return [make_relevant("b0", 0.5)]
            return [make_relevant(f"a{i}", 0.5) for i in range(20)]
        document_repo.relevant_documents.side_effect = per_topic

        result = await service.load_dashboard(make_query(topics=["a", "b"], sample_size=10))
        topics = [r.topic for r in result.relevant_documents]
        assert len(result.relevant_documents) == 10
        assert topics.count("b") == 1
        assert topics.count("a") == 9


# ---------------------------------------------------------------------------
# _apportion_slots (pure apportionment logic)
# ---------------------------------------------------------------------------

class TestApportionSlots:
    def test_sums_to_sample_size(self):
        slots = VisualisationService._apportion_slots({"a": 0.9, "b": 0.3, "c": 0.5}, 30)
        assert sum(slots.values()) == 30

    def test_minimum_one_per_topic(self):
        slots = VisualisationService._apportion_slots({"a": 1.0, "b": 0.0}, 10)
        assert slots["b"] == 1
        assert slots["a"] == 9

    def test_proportional_allocation(self):
        slots = VisualisationService._apportion_slots({"a": 0.9, "b": 0.3}, 12)
        assert slots["a"] > slots["b"]

    def test_zero_total_weight_spreads_evenly(self):
        slots = VisualisationService._apportion_slots({"a": 0.0, "b": 0.0}, 10)
        assert slots == {"a": 5, "b": 5}

    def test_sample_size_equal_to_topic_count(self):
        slots = VisualisationService._apportion_slots({"a": 0.9, "b": 0.3}, 2)
        assert slots == {"a": 1, "b": 1}


# ---------------------------------------------------------------------------
# _diversify_by_platform (pure interleaving logic)
# ---------------------------------------------------------------------------

class TestDiversifyByPlatform:
    def test_single_platform_unchanged(self):
        docs = [make_relevant(f"d{i}", 0.9 - i / 10, platform="twitter") for i in range(3)]
        assert VisualisationService._diversify_by_platform(docs) == docs

    def test_interleaves_platforms_keeping_relevance_head(self):
        docs = [
            make_relevant("t1", 0.9, platform="twitter"),
            make_relevant("t2", 0.8, platform="twitter"),
            make_relevant("g1", 0.5, platform="telegram"),
        ]
        order = [d["doc_id"] for d in VisualisationService._diversify_by_platform(docs)]
        # Highest-relevance doc stays first; the second platform is pulled ahead of the
        # second twitter doc.
        assert order == ["t1", "g1", "t2"]

    def test_empty_list(self):
        assert VisualisationService._diversify_by_platform([]) == []
