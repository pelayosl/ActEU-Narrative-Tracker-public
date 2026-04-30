from datetime import datetime, timezone

import pytest

from app.repositories.document_repository import DocumentRepository
from app.schemas.search import SearchQuery

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc(**overrides) -> dict:
    """Return a minimal valid document. Override any field as needed."""
    base = {
        "headline": "Default headline",
        "plain_text": "Default plain text content.",
        "platform": "twitter",
        "country": "ES",
        "language": "es",
        "published_time": datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        "author": "testuser",
        "acteu_topic": {"label": "immigration", "confidence": 0.8},
        "named_entities": [],
        "sentiment": "neutral",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def repo(db):
    return DocumentRepository(db)


@pytest.fixture
async def populated(db, repo):
    """Insert a standard set of documents and return their inserted ids as strings."""
    docs = [
        make_doc(
            headline="Immigration debate in Spain",
            plain_text="Spain is discussing new immigration laws.",
            platform="twitter",
            country="ES",
            language="es",
            published_time=datetime(2024, 1, 10, tzinfo=timezone.utc),
            acteu_topic={"label": "immigration", "confidence": 0.9},
            sentiment="negative",
        ),
        make_doc(
            headline="Climate summit in Germany",
            plain_text="Germany hosts a major climate change conference.",
            platform="telegram",
            country="DE",
            language="de",
            published_time=datetime(2024, 3, 20, tzinfo=timezone.utc),
            acteu_topic={"label": "climate_change", "confidence": 0.85},
            sentiment="positive",
        ),
        make_doc(
            headline="Gender equality march",
            plain_text="Thousands march for gender issues and equality rights.",
            platform="media",
            country="FR",
            language="fr",
            published_time=datetime(2024, 6, 1, tzinfo=timezone.utc),
            acteu_topic={"label": "gender_issues", "confidence": 0.75},
            sentiment="positive",
        ),
    ]
    result = await db["documents"].insert_many(docs)
    return [str(oid) for oid in result.inserted_ids]


# ---------------------------------------------------------------------------
# find()
# ---------------------------------------------------------------------------

class TestFind:
    async def test_no_filter_returns_all(self, repo, populated):
        results = await repo.find(SearchQuery())
        assert len(results) == 3

    async def test_keyword_matches_headline(self, repo, populated):
        results = await repo.find(SearchQuery(keywords=["summit"]))
        assert len(results) == 1
        assert "summit" in results[0]["headline"].lower()

    async def test_keyword_matches_plain_text(self, repo, populated):
        results = await repo.find(SearchQuery(keywords=["equality"]))
        assert len(results) == 1
        assert "equality" in results[0]["plain_text"].lower()

    async def test_keyword_is_case_insensitive(self, repo, populated):
        results = await repo.find(SearchQuery(keywords=["CLIMATE"]))
        assert len(results) == 1

    async def test_keyword_no_match_returns_empty(self, repo, populated):
        results = await repo.find(SearchQuery(keywords=["nonexistentterm"]))
        assert results == []

    async def test_date_from_filters_older_docs(self, repo, populated):
        results = await repo.find(SearchQuery(date_from=datetime(2024, 3, 1, tzinfo=timezone.utc)))
        # MongoDB returns datetimes as timezone-naive; compare without tzinfo
        assert all(doc["published_time"] >= datetime(2024, 3, 1) for doc in results)
        assert len(results) == 2

    async def test_date_to_filters_newer_docs(self, repo, populated):
        results = await repo.find(SearchQuery(date_to=datetime(2024, 2, 1, tzinfo=timezone.utc)))
        assert len(results) == 1
        assert results[0]["country"] == "ES"

    async def test_date_range_inclusive(self, repo, populated):
        results = await repo.find(SearchQuery(
            date_from=datetime(2024, 1, 10, tzinfo=timezone.utc),
            date_to=datetime(2024, 3, 20, tzinfo=timezone.utc),
        ))
        assert len(results) == 2

    async def test_platform_filter(self, repo, populated):
        results = await repo.find(SearchQuery(platforms=["telegram"]))
        assert len(results) == 1
        assert results[0]["platform"] == "telegram"

    async def test_platform_filter_multiple(self, repo, populated):
        results = await repo.find(SearchQuery(platforms=["twitter", "media"]))
        assert len(results) == 2

    async def test_topic_filter(self, repo, populated):
        results = await repo.find(SearchQuery(topics=["climate_change"]))
        assert len(results) == 1
        assert results[0]["acteu_topic"]["label"] == "climate_change"

    async def test_topic_filter_multiple(self, repo, populated):
        results = await repo.find(SearchQuery(topics=["immigration", "gender_issues"]))
        assert len(results) == 2

    async def test_combined_filters_and_logic(self, repo, populated):
        results = await repo.find(SearchQuery(platforms=["twitter"], topics=["immigration"]))
        assert len(results) == 1
        assert results[0]["country"] == "ES"

    async def test_combined_filters_no_match(self, repo, populated):
        results = await repo.find(SearchQuery(platforms=["telegram"], topics=["gender_issues"]))
        assert results == []

    async def test_results_sorted_by_date_descending(self, repo, populated):
        results = await repo.find(SearchQuery())
        dates = [doc["published_time"] for doc in results]
        assert dates == sorted(dates, reverse=True)

    async def test_language_filter(self, repo, populated):
        results = await repo.find(SearchQuery(languages=["de"]))
        assert len(results) == 1
        assert results[0]["language"] == "de"

    async def test_empty_collection_returns_empty(self, repo):
        results = await repo.find(SearchQuery())
        assert results == []


# ---------------------------------------------------------------------------
# find_by_ids()
# ---------------------------------------------------------------------------

class TestFindByIds:
    async def test_returns_matching_documents(self, repo, populated):
        results = await repo.find_by_ids(populated[:2])
        assert len(results) == 2

    async def test_returns_all_three(self, repo, populated):
        results = await repo.find_by_ids(populated)
        assert len(results) == 3

    async def test_invalid_id_is_skipped(self, repo, populated):
        ids = populated[:1] + ["not-a-valid-objectid"]
        results = await repo.find_by_ids(ids)
        assert len(results) == 1

    async def test_all_invalid_ids_returns_empty(self, repo, populated):
        results = await repo.find_by_ids(["bad", "ids", "here"])
        assert results == []

    async def test_empty_list_returns_empty(self, repo):
        results = await repo.find_by_ids([])
        assert results == []

    async def test_unknown_valid_objectid_returns_empty(self, repo):
        from bson import ObjectId
        results = await repo.find_by_ids([str(ObjectId())])
        assert results == []


# ---------------------------------------------------------------------------
# count()
# ---------------------------------------------------------------------------

class TestCount:
    async def test_count_no_filter(self, repo, populated):
        assert await repo.count(SearchQuery()) == 3

    async def test_count_with_topic_filter(self, repo, populated):
        assert await repo.count(SearchQuery(topics=["immigration"])) == 1

    async def test_count_with_no_match(self, repo, populated):
        assert await repo.count(SearchQuery(keywords=["zzznomatch"])) == 0

    async def test_count_empty_collection(self, repo):
        assert await repo.count(SearchQuery()) == 0


# ---------------------------------------------------------------------------
# get_excerpt()
# ---------------------------------------------------------------------------

class TestGetExcerpt:
    async def test_short_text_returned_verbatim(self, db, repo):
        text = "Short text."
        result = await db["documents"].insert_one(make_doc(plain_text=text))
        excerpt = await repo.get_excerpt(str(result.inserted_id))
        assert excerpt == text

    async def test_long_text_is_truncated(self, db, repo):
        text = "A" * 300
        result = await db["documents"].insert_one(make_doc(plain_text=text))
        excerpt = await repo.get_excerpt(str(result.inserted_id))
        assert len(excerpt) <= 253  # 250 chars + "..."
        assert excerpt.endswith("...")

    async def test_exactly_250_chars_not_truncated(self, db, repo):
        text = "B" * 250
        result = await db["documents"].insert_one(make_doc(plain_text=text))
        excerpt = await repo.get_excerpt(str(result.inserted_id))
        assert excerpt == text
        assert not excerpt.endswith("...")

    async def test_invalid_id_returns_empty_string(self, repo):
        excerpt = await repo.get_excerpt("not-a-valid-id")
        assert excerpt == ""

    async def test_unknown_id_returns_empty_string(self, repo):
        from bson import ObjectId
        excerpt = await repo.get_excerpt(str(ObjectId()))
        assert excerpt == ""
