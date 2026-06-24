"""Integration tests for the /search router."""

from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.integration


async def insert_project(db, *, project_id, owner_id):
    await db["projects"].insert_one(
        {
            "project_id": project_id,
            "owner_id": owner_id,
            "name": "P",
            "created_at": datetime.now(timezone.utc),
            "classifiers": [],
            "document_proxies": [],
            "pending_pipeline": None,
        }
    )


# ---------------------------------------------------------------------------
# POST /search/
# ---------------------------------------------------------------------------

class TestSearch:
    async def test_empty_query_returns_result_shape(self, auth_client):
        res = await auth_client.post("/search/", json={"keywords": [], "topics": []})

        assert res.status_code == 200
        body = res.json()
        assert body["total_docs"] == 0
        assert body["retrieved_docs"] == []

    async def test_finds_seeded_document(self, auth_client, db):
        await db["documents"].insert_one(
            {
                "_id": "doc-1",
                "plain_text": "immigration policy in europe",
                "platform": "twitter",
                "language": "en",
                "published_time": datetime(2024, 4, 20, tzinfo=timezone.utc),
                "acteu_topic": {"label": "immigration", "confidence": 0.9},
            }
        )

        res = await auth_client.post(
            "/search/", json={"keywords": [], "topics": ["immigration"]}
        )

        assert res.status_code == 200
        body = res.json()
        assert body["total_docs"] == 1
        assert body["retrieved_docs"][0]["doc_id"] == "doc-1"

    async def test_malformed_query_returns_422(self, auth_client):
        # topics must be a list of strings
        res = await auth_client.post("/search/", json={"topics": "immigration"})
        assert res.status_code == 422

    async def test_subtopics_with_unknown_project_returns_404(self, auth_client):
        res = await auth_client.post(
            "/search/?project_id=missing", json={"subtopics": ["s-1"]}
        )
        assert res.status_code == 404

    async def test_subtopics_with_other_owner_project_returns_403(self, auth_client, db):
        await insert_project(db, project_id="p-other", owner_id="another-user")

        res = await auth_client.post(
            "/search/?project_id=p-other", json={"subtopics": ["s-1"]}
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# GET /search/languages
# ---------------------------------------------------------------------------

class TestLanguages:
    async def test_returns_distinct_languages(self, auth_client, db):
        await db["documents"].insert_many(
            [
                {"_id": "d1", "language": "en", "platform": "x", "plain_text": ""},
                {"_id": "d2", "language": "es", "platform": "x", "plain_text": ""},
                {"_id": "d3", "language": "en", "platform": "x", "plain_text": ""},
            ]
        )

        res = await auth_client.get("/search/languages")

        assert res.status_code == 200
        assert sorted(res.json()) == ["en", "es"]

    async def test_requires_auth(self, client):
        res = await client.get("/search/languages")
        assert res.status_code in (401, 403)
