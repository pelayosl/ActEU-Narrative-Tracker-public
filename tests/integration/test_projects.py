"""Integration tests for the /projects router (and project-scoped classifier sub-routes)."""

import os
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def insert_project(db, *, project_id, owner_id, name="P", classifiers=None):
    doc = {
        "project_id": project_id,
        "owner_id": owner_id,
        "name": name,
        "created_at": datetime.now(timezone.utc),
        "classifiers": classifiers or [],
        "document_proxies": [],
        "pending_pipeline": None,
    }
    await db["projects"].insert_one(doc)
    return doc


def classifier_doc(classifier_id, name, file_path):
    return {
        "classifier_id": classifier_id,
        "name": name,
        "topics": [],
        "file_path": file_path,
        "created_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# POST /projects  (name as query param)  &  GET /projects
# ---------------------------------------------------------------------------

class TestCreateAndList:
    async def test_create_returns_201_and_persists(self, auth_client, db, current_user):
        res = await auth_client.post("/projects?name=My%20Project")

        assert res.status_code == 201
        body = res.json()
        assert body["name"] == "My Project"
        assert body["owner_id"] == current_user.user_id
        assert await db["projects"].find_one({"project_id": body["project_id"]}) is not None

    async def test_list_returns_only_owner_projects(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-own", owner_id=current_user.user_id)
        await insert_project(db, project_id="p-other", owner_id="someone-else")

        res = await auth_client.get("/projects")

        assert res.status_code == 200
        ids = {p["project_id"] for p in res.json()}
        assert ids == {"p-own"}

    async def test_empty_name_returns_422(self, auth_client):
        # Alt 10.1: a project name is mandatory (backend guard, empty and whitespace-only).
        res = await auth_client.post("/projects?name=")
        assert res.status_code == 422

        res = await auth_client.post("/projects?name=%20%20")
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# GET /projects/{id}
# ---------------------------------------------------------------------------

class TestGetProject:
    async def test_owner_gets_project(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-1", owner_id=current_user.user_id, name="Mine")

        res = await auth_client.get("/projects/p-1")

        assert res.status_code == 200
        assert res.json()["name"] == "Mine"

    async def test_unknown_project_returns_404(self, auth_client):
        res = await auth_client.get("/projects/missing")
        assert res.status_code == 404

    async def test_other_owner_returns_403(self, auth_client, db):
        await insert_project(db, project_id="p-2", owner_id="another-user")

        res = await auth_client.get("/projects/p-2")

        assert res.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /projects/{id}
# ---------------------------------------------------------------------------

class TestDeleteProject:
    async def test_owner_deletes_204(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-del", owner_id=current_user.user_id)

        res = await auth_client.delete("/projects/p-del")

        assert res.status_code == 204
        assert await db["projects"].find_one({"project_id": "p-del"}) is None

    async def test_other_owner_403(self, auth_client, db):
        await insert_project(db, project_id="p-x", owner_id="another-user")

        res = await auth_client.delete("/projects/p-x")

        assert res.status_code == 403


# ---------------------------------------------------------------------------
# Classifier sub-resource: download / delete
# ---------------------------------------------------------------------------

class TestClassifierRoutes:
    async def test_download_streams_file(self, auth_client, db, current_user, tmp_path):
        bin_path = tmp_path / "model.bin"
        bin_path.write_bytes(b"FASTTEXT-BINARY")
        await insert_project(
            db,
            project_id="p-c",
            owner_id=current_user.user_id,
            classifiers=[classifier_doc("c-1", "MyClf", str(bin_path))],
        )

        res = await auth_client.get("/projects/p-c/classifiers/c-1/download")

        assert res.status_code == 200
        assert res.content == b"FASTTEXT-BINARY"

    async def test_download_unknown_classifier_404(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-c2", owner_id=current_user.user_id)

        res = await auth_client.get("/projects/p-c2/classifiers/ghost/download")

        assert res.status_code == 404

    async def test_download_missing_file_404(self, auth_client, db, current_user):
        await insert_project(
            db,
            project_id="p-c3",
            owner_id=current_user.user_id,
            classifiers=[classifier_doc("c-3", "Clf", "/no/such/file.bin")],
        )

        res = await auth_client.get("/projects/p-c3/classifiers/c-3/download")

        assert res.status_code == 404

    async def test_delete_classifier_204(self, auth_client, db, current_user, tmp_path):
        bin_path = tmp_path / "m.bin"
        bin_path.write_bytes(b"x")
        await insert_project(
            db,
            project_id="p-c4",
            owner_id=current_user.user_id,
            classifiers=[classifier_doc("c-4", "Clf", str(bin_path))],
        )

        res = await auth_client.delete("/projects/p-c4/classifiers/c-4")

        assert res.status_code == 204
        project = await db["projects"].find_one({"project_id": "p-c4"})
        assert project["classifiers"] == []

    async def test_delete_unknown_classifier_404(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-c5", owner_id=current_user.user_id)

        res = await auth_client.delete("/projects/p-c5/classifiers/ghost")

        assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{id}/topics  (facet shape)
# ---------------------------------------------------------------------------

class TestProjectTopics:
    async def test_returns_searchtopics_shape(self, auth_client, db, current_user):
        await insert_project(db, project_id="p-t", owner_id=current_user.user_id)
        # 3 core topics seeded so the facet has the core entries
        await db["topics"].insert_many(
            [
                {"topic_id": "immigration", "name": "Immigration", "description": "",
                 "origin_topic_ids": [], "core_topic": "immigration"},
                {"topic_id": "climate_change", "name": "Climate", "description": "",
                 "origin_topic_ids": [], "core_topic": "climate_change"},
                {"topic_id": "gender_issues", "name": "Gender", "description": "",
                 "origin_topic_ids": [], "core_topic": "gender_issues"},
            ]
        )

        res = await auth_client.get("/projects/p-t/topics")

        assert res.status_code == 200
        body = res.json()
        assert "core_topics" in body and "subtopics" in body
        assert len(body["core_topics"]) == 3
