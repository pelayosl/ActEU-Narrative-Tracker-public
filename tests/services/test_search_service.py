from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from app.schemas.search import SearchQuery, SearchResult
from app.services.search_service import SearchService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_raw_doc(**overrides) -> dict:
    """A raw document as it would come back from MongoDB (with ObjectId _id)."""
    base = {
        "_id": ObjectId(),
        "headline": "Headline",
        "plain_text": "Some plain text content.",
        "platform": "twitter",
        "language": "en",
        "country": "ES",
        "published_time": datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        "acteu_topic": {"label": "immigration", "confidence": 0.8},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(repo) -> SearchService:
    return SearchService(repo)


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------

class TestSearch:
    async def test_returns_search_result(self, service, repo):
        repo.find.return_value = [make_raw_doc()]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())

        assert isinstance(result, SearchResult)
        assert result.total_docs == 1
        assert len(result.retrieved_docs) == 1

    async def test_total_docs_is_repo_count_not_retrieved_length(self, service, repo):
        """`total_docs` reflects the full match count, not the (possibly capped) returned slice."""
        repo.find.return_value = [make_raw_doc(), make_raw_doc()]
        repo.count.return_value = 42

        result = await service.search(SearchQuery())

        assert result.total_docs == 42
        assert len(result.retrieved_docs) == 2

    async def test_empty_results(self, service, repo):
        repo.find.return_value = []
        repo.count.return_value = 0

        result = await service.search(SearchQuery())

        assert result.total_docs == 0
        assert result.retrieved_docs == []

    async def test_query_is_forwarded_to_repo(self, service, repo):
        repo.find.return_value = []
        repo.count.return_value = 0
        query = SearchQuery(keywords=["climate"], confidence_threshold=0.7)

        await service.search(query)

        repo.find.assert_awaited_once_with(query)
        repo.count.assert_awaited_once_with(query)


# ---------------------------------------------------------------------------
# _to_summary() (covered via search())
# ---------------------------------------------------------------------------

class TestToSummary:
    async def test_maps_basic_fields(self, service, repo):
        oid = ObjectId()
        repo.find.return_value = [make_raw_doc(
            _id=oid,
            headline="My headline",
            platform="telegram",
            language="de",
            published_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
        )]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        summary = result.retrieved_docs[0]

        assert summary.doc_id == str(oid)
        assert summary.headline == "My headline"
        assert summary.platform == "telegram"
        assert summary.language == "de"

    async def test_short_text_returned_verbatim(self, service, repo):
        repo.find.return_value = [make_raw_doc(plain_text="Short content.")]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].excerpt == "Short content."

    async def test_long_text_truncated_with_ellipsis(self, service, repo):
        repo.find.return_value = [make_raw_doc(plain_text="A" * 300)]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        excerpt = result.retrieved_docs[0].excerpt
        assert excerpt.endswith("...")
        assert len(excerpt) <= 253

    async def test_exactly_250_chars_not_truncated(self, service, repo):
        text = "B" * 250
        repo.find.return_value = [make_raw_doc(plain_text=text)]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].excerpt == text

    async def test_truncation_rstrips_trailing_whitespace(self, service, repo):
        repo.find.return_value = [make_raw_doc(plain_text="A" * 249 + " " + "B" * 100)]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        excerpt = result.retrieved_docs[0].excerpt
        # Position 249 is a space, gets rstripped before the ellipsis is appended.
        assert excerpt == "A" * 249 + "..."

    async def test_plain_text_is_stripped(self, service, repo):
        repo.find.return_value = [make_raw_doc(plain_text="   hello   ")]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].excerpt == "hello"

    async def test_missing_plain_text_yields_empty_excerpt(self, service, repo):
        doc = make_raw_doc()
        doc.pop("plain_text")
        repo.find.return_value = [doc]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].excerpt == ""

    async def test_null_plain_text_yields_empty_excerpt(self, service, repo):
        repo.find.return_value = [make_raw_doc(plain_text=None)]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].excerpt == ""

    async def test_missing_headline_defaults_to_empty(self, service, repo):
        doc = make_raw_doc()
        doc.pop("headline")
        repo.find.return_value = [doc]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].headline == ""

    async def test_null_headline_defaults_to_empty(self, service, repo):
        repo.find.return_value = [make_raw_doc(headline=None)]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].headline == ""

    async def test_missing_platform_defaults_to_empty(self, service, repo):
        doc = make_raw_doc()
        doc.pop("platform")
        repo.find.return_value = [doc]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].platform == ""

    async def test_missing_language_defaults_to_empty(self, service, repo):
        doc = make_raw_doc()
        doc.pop("language")
        repo.find.return_value = [doc]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].language == ""

    async def test_acteu_topic_label_propagated(self, service, repo):
        repo.find.return_value = [make_raw_doc(
            acteu_topic={"label": "climate_change", "confidence": 0.9}
        )]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].relevant_topics == ["climate_change"]

    async def test_missing_acteu_topic_yields_empty_relevant_topics(self, service, repo):
        doc = make_raw_doc()
        doc.pop("acteu_topic")
        repo.find.return_value = [doc]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].relevant_topics == []

    async def test_null_acteu_topic_yields_empty_relevant_topics(self, service, repo):
        repo.find.return_value = [make_raw_doc(acteu_topic=None)]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].relevant_topics == []

    async def test_acteu_topic_without_label_yields_empty_relevant_topics(self, service, repo):
        repo.find.return_value = [make_raw_doc(acteu_topic={"confidence": 0.9})]
        repo.count.return_value = 1

        result = await service.search(SearchQuery())
        assert result.retrieved_docs[0].relevant_topics == []


# ---------------------------------------------------------------------------
# get_documents_by_ids()
# ---------------------------------------------------------------------------

class TestGetDocumentsByIds:
    async def test_delegates_to_repo(self, service, repo):
        expected = [make_raw_doc(), make_raw_doc()]
        repo.find_by_ids.return_value = expected

        result = await service.get_documents_by_ids(["a", "b"])

        assert result == expected
        repo.find_by_ids.assert_awaited_once_with(["a", "b"])

    async def test_empty_list_forwarded(self, service, repo):
        repo.find_by_ids.return_value = []
        result = await service.get_documents_by_ids([])
        assert result == []
        repo.find_by_ids.assert_awaited_once_with([])
