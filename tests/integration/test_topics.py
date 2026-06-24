"""Integration tests for the /topics router (generation + reconciliation dispatch)."""

from datetime import datetime, timezone

import pytest

from tests.integration.conftest import FAKE_JOB_ID

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


def topic(topic_id, name):
    return {"topic_id": topic_id, "name": name, "description": "", "origin_topic_ids": []}


# ---------------------------------------------------------------------------
# POST /topics/generate
# ---------------------------------------------------------------------------

class TestGenerate:
    async def test_dispatches_and_returns_job_id(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-g", owner_id=current_user.user_id)

        res = await auth_client.post(
            "/topics/generate",
            json={"project_id": "p-g", "doc_ids": ["d1", "d2"]},
        )

        assert res.status_code == 200
        assert res.json() == {"job_id": FAKE_JOB_ID}

    async def test_unknown_project_404(self, auth_client):
        res = await auth_client.post(
            "/topics/generate", json={"project_id": "ghost", "doc_ids": []}
        )
        assert res.status_code == 404

    async def test_other_owner_403(self, auth_client, db):
        await insert_project(db, project_id="p-g2", owner_id="another-user")

        res = await auth_client.post(
            "/topics/generate", json={"project_id": "p-g2", "doc_ids": []}
        )
        assert res.status_code == 403

    async def test_malformed_body_422(self, auth_client):
        res = await auth_client.post("/topics/generate", json={"doc_ids": []})
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# POST /topics/reconcile
# ---------------------------------------------------------------------------

class TestReconcile:
    async def test_dispatches_and_returns_job_id(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-r", owner_id=current_user.user_id)

        res = await auth_client.post(
            "/topics/reconcile",
            json={"project_id": "p-r", "topics": [topic("t1", "A"), topic("t2", "B")]},
        )

        assert res.status_code == 200
        assert res.json() == {"job_id": FAKE_JOB_ID}

    async def test_unknown_project_404(self, auth_client):
        res = await auth_client.post(
            "/topics/reconcile", json={"project_id": "ghost", "topics": []}
        )
        assert res.status_code == 404
