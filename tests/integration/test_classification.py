"""Integration tests for the /classification router.

Training and Phase-2 labelling only need to prove "valid request -> dispatch -> {job_id}"
(the dispatch service is faked in conftest). Phase-1 labelling (`/label/initial`) runs the
real ProjectService against the test DB so we can cover its three documented error mappings.
"""

from datetime import datetime, timezone

import pytest

from tests.integration.conftest import FAKE_JOB_ID

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def topic(topic_id, name):
    return {"topic_id": topic_id, "name": name, "description": "", "origin_topic_ids": []}


async def insert_project(db, *, project_id, owner_id, classifiers=None, pending_pipeline=None):
    await db["projects"].insert_one(
        {
            "project_id": project_id,
            "owner_id": owner_id,
            "name": "P",
            "created_at": datetime.now(timezone.utc),
            "classifiers": classifiers or [],
            "document_proxies": [],
            "pending_pipeline": pending_pipeline,
        }
    )


def classifier_doc(classifier_id, topics):
    return {
        "classifier_id": classifier_id,
        "name": "Clf",
        "topics": topics,
        "file_path": "/x.bin",
        "created_at": datetime.now(timezone.utc),
    }


def pipeline_doc(*, classifier_id, topic_mapping):
    return {
        "generation_job_id": "g-1",
        "generated_topics": [],
        "reconciled_topics": [],
        "topic_mapping": topic_mapping,
        "created_at": datetime.now(timezone.utc),
        "classifier_id": classifier_id,
    }


# ---------------------------------------------------------------------------
# POST /classification/train
# ---------------------------------------------------------------------------

class TestTrain:
    async def test_dispatches_and_returns_job_id(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-tr", owner_id=current_user.user_id)

        res = await auth_client.post(
            "/classification/train",
            json={"project_id": "p-tr", "name": "Clf", "topics": [topic("t1", "A")]},
        )

        assert res.status_code == 200
        assert res.json() == {"job_id": FAKE_JOB_ID}

    async def test_other_owner_403(self, auth_client, db):
        await insert_project(db, project_id="p-tr2", owner_id="another-user")

        res = await auth_client.post(
            "/classification/train",
            json={"project_id": "p-tr2", "name": "Clf", "topics": []},
        )
        assert res.status_code == 403

    async def test_unknown_project_404(self, auth_client):
        res = await auth_client.post(
            "/classification/train",
            json={"project_id": "ghost", "name": "Clf", "topics": []},
        )
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# POST /classification/label/initial  (Phase 1, synchronous, real stack)
# ---------------------------------------------------------------------------

class TestInitialLabels:
    async def test_success_returns_labelling_result_and_clears_pipeline(
        self, auth_client, db, current_user
    ):
        await insert_project(
            db,
            project_id="p-l1",
            owner_id=current_user.user_id,
            classifiers=[classifier_doc("c-1", [topic("t1", "Immigration")])],
            pending_pipeline=pipeline_doc(
                classifier_id="c-1", topic_mapping={"t1": ["doc-a", "doc-b"]}
            ),
        )

        res = await auth_client.post(
            "/classification/label/initial",
            json={"project_id": "p-l1", "classifier_id": "c-1"},
        )

        assert res.status_code == 200
        body = res.json()
        assert body["project_id"] == "p-l1"
        assert body["total_labelled"] == 2
        # pipeline cleared on success
        project = await db["projects"].find_one({"project_id": "p-l1"})
        assert project["pending_pipeline"] is None

    async def test_no_pending_pipeline_returns_409(self, auth_client, db, current_user):
        await insert_project(
            db,
            project_id="p-l2",
            owner_id=current_user.user_id,
            classifiers=[classifier_doc("c-1", [])],
            pending_pipeline=None,
        )

        res = await auth_client.post(
            "/classification/label/initial",
            json={"project_id": "p-l2", "classifier_id": "c-1"},
        )
        assert res.status_code == 409

    async def test_unknown_classifier_returns_404(self, auth_client, db, current_user):
        await insert_project(
            db,
            project_id="p-l3",
            owner_id=current_user.user_id,
            classifiers=[],
            pending_pipeline=pipeline_doc(classifier_id="c-1", topic_mapping={}),
        )

        res = await auth_client.post(
            "/classification/label/initial",
            json={"project_id": "p-l3", "classifier_id": "ghost"},
        )
        assert res.status_code == 404

    async def test_pipeline_mismatch_returns_409(self, auth_client, db, current_user):
        # pipeline belongs to a different (newer) classifier id
        await insert_project(
            db,
            project_id="p-l4",
            owner_id=current_user.user_id,
            classifiers=[classifier_doc("c-1", [topic("t1", "A")])],
            pending_pipeline=pipeline_doc(classifier_id="c-NEWER", topic_mapping={"t1": ["d"]}),
        )

        res = await auth_client.post(
            "/classification/label/initial",
            json={"project_id": "p-l4", "classifier_id": "c-1"},
        )
        assert res.status_code == 409


# ---------------------------------------------------------------------------
# POST /classification/label  (Phase 2, async dispatch)
# ---------------------------------------------------------------------------

class TestLabelByQuery:
    async def test_dispatches_when_classifier_exists(self, auth_client, db, current_user):
        await insert_project(
            db,
            project_id="p-l5",
            owner_id=current_user.user_id,
            classifiers=[classifier_doc("c-1", [])],
        )

        res = await auth_client.post(
            "/classification/label",
            json={"project_id": "p-l5", "classifier_id": "c-1", "query": {"keywords": []}},
        )

        assert res.status_code == 200
        assert res.json() == {"job_id": FAKE_JOB_ID}

    async def test_unknown_classifier_404(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-l6", owner_id=current_user.user_id, classifiers=[])

        res = await auth_client.post(
            "/classification/label",
            json={"project_id": "p-l6", "classifier_id": "ghost", "query": {"keywords": []}},
        )
        assert res.status_code == 404
