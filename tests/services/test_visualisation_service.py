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

    async def test_unimplemented_blocks_are_empty(self, service):
        result = await service.load_dashboard(make_query())
        assert result.topics_by_platform == []
        assert result.top_actors == []
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
