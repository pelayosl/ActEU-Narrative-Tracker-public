import pytest

from app.repositories.project_repository import ProjectRepository


@pytest.fixture
async def repo(db):
    return ProjectRepository(db)


def make_proxy(doc_id: str, *labels) -> dict:
    """labels: tuples of (topic_id, name)."""
    return {
        "doc_id": doc_id,
        "labels": [
            {
                "topic_id": tid,
                "name": name,
                "description": "",
                "classifier_id": "c1",
                "confidence": 0.9,
            }
            for tid, name in labels
        ],
    }


async def insert_project(db, project_id: str, proxies: list[dict]) -> None:
    await db["projects"].insert_one({
        "project_id": project_id,
        "owner_id": "u1",
        "name": "P",
        "created_at": "2024-01-01T00:00:00",
        "classifiers": [],
        "document_proxies": proxies,
        "pending_pipeline": None,
    })


class TestFindProxyDocIdsByTopics:
    async def test_matches_by_topic_id(self, db, repo):
        await insert_project(db, "p1", [
            make_proxy("d1", ("sub-a", "Wind energy")),
            make_proxy("d2", ("sub-b", "Solar energy")),
        ])
        result = await repo.find_proxy_doc_ids_by_topics("p1", ["sub-a"])
        assert result == {"sub-a": ["d1"]}

    async def test_does_not_match_by_name(self, db, repo):
        await insert_project(db, "p1", [
            make_proxy("d1", ("sub-a", "Wind energy")),
        ])
        result = await repo.find_proxy_doc_ids_by_topics("p1", ["Wind energy"])
        assert result == {}

    async def test_multiple_docs_per_topic(self, db, repo):
        await insert_project(db, "p1", [
            make_proxy("d1", ("sub-a", "Wind energy")),
            make_proxy("d2", ("sub-a", "Wind energy")),
        ])
        result = await repo.find_proxy_doc_ids_by_topics("p1", ["sub-a"])
        assert set(result["sub-a"]) == {"d1", "d2"}

    async def test_omits_topics_without_match(self, db, repo):
        await insert_project(db, "p1", [make_proxy("d1", ("sub-a", "Wind energy"))])
        result = await repo.find_proxy_doc_ids_by_topics("p1", ["sub-a", "sub-z"])
        assert "sub-z" not in result
        assert result == {"sub-a": ["d1"]}

    async def test_unknown_project_returns_empty(self, db, repo):
        result = await repo.find_proxy_doc_ids_by_topics("nope", ["sub-a"])
        assert result == {}

    async def test_no_proxies_returns_empty(self, db, repo):
        await insert_project(db, "p1", [])
        result = await repo.find_proxy_doc_ids_by_topics("p1", ["sub-a"])
        assert result == {}
