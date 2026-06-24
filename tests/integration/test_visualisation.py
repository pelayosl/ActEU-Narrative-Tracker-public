"""Integration tests for the /visualisation router."""

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


VIS_QUERY = {
    "topics": ["immigration"],
    "date_from": "2024-01-01T00:00:00",
    "date_to": "2024-12-31T00:00:00",
    "languages": [],
    "platforms": [],
}


class TestLoadDashboard:
    async def test_returns_dashboard_shape(self, auth_client):
        res = await auth_client.post("/visualisation/", json=VIS_QUERY)

        assert res.status_code == 200
        body = res.json()
        for key in (
            "topic_evolution",
            "topics_by_language",
            "topics_by_platform",
            "top_entities",
            "relevant_documents",
        ):
            assert key in body

    async def test_with_project_scope_ok(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-v", owner_id=current_user.user_id)

        res = await auth_client.post("/visualisation/?project_id=p-v", json=VIS_QUERY)

        assert res.status_code == 200

    async def test_unknown_project_404(self, auth_client):
        res = await auth_client.post("/visualisation/?project_id=ghost", json=VIS_QUERY)
        assert res.status_code == 404

    async def test_other_owner_403(self, auth_client, db):
        await insert_project(db, project_id="p-v2", owner_id="another-user")

        res = await auth_client.post("/visualisation/?project_id=p-v2", json=VIS_QUERY)
        assert res.status_code == 403

    async def test_requires_auth(self, client):
        res = await client.post("/visualisation/", json=VIS_QUERY)
        assert res.status_code in (401, 403)
