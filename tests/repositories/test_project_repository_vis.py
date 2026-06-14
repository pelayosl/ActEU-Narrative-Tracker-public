import pytest

from app.repositories.project_repository import ProjectRepository


@pytest.fixture
async def repo(db):
    return ProjectRepository(db)


def make_proxy(doc_id: str, *labels) -> dict:
    """labels: tuples of (topic_id, name) or (topic_id, name, confidence)."""
    def label(parts):
        tid, name = parts[0], parts[1]
        confidence = parts[2] if len(parts) > 2 else 0.9
        return {
            "topic_id": tid,
            "name": name,
            "description": "",
            "classifier_id": "c1",
            "confidence": confidence,
        }

    return {"doc_id": doc_id, "labels": [label(lbl) for lbl in labels]}


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


class TestFindProxyConfidenceByTopics:
    async def test_matches_by_topic_id(self, db, repo):
        await insert_project(db, "p1", [
            make_proxy("d1", ("sub-a", "Wind energy", 0.75)),
            make_proxy("d2", ("sub-b", "Solar energy", 0.6)),
        ])
        result = await repo.find_proxy_confidence_by_topics("p1", ["sub-a"])
        assert result == {"sub-a": {"d1": 0.75}}

    async def test_does_not_match_by_name(self, db, repo):
        await insert_project(db, "p1", [
            make_proxy("d1", ("sub-a", "Wind energy")),
        ])
        result = await repo.find_proxy_confidence_by_topics("p1", ["Wind energy"])
        assert result == {}

    async def test_multiple_docs_per_topic(self, db, repo):
        await insert_project(db, "p1", [
            make_proxy("d1", ("sub-a", "Wind energy", 0.8)),
            make_proxy("d2", ("sub-a", "Wind energy", 0.4)),
        ])
        result = await repo.find_proxy_confidence_by_topics("p1", ["sub-a"])
        assert result["sub-a"] == {"d1": 0.8, "d2": 0.4}

    async def test_omits_topics_without_match(self, db, repo):
        await insert_project(db, "p1", [make_proxy("d1", ("sub-a", "Wind energy", 0.5))])
        result = await repo.find_proxy_confidence_by_topics("p1", ["sub-a", "sub-z"])
        assert "sub-z" not in result
        assert result == {"sub-a": {"d1": 0.5}}

    async def test_unknown_project_returns_empty(self, db, repo):
        result = await repo.find_proxy_confidence_by_topics("nope", ["sub-a"])
        assert result == {}

    async def test_no_proxies_returns_empty(self, db, repo):
        await insert_project(db, "p1", [])
        result = await repo.find_proxy_confidence_by_topics("p1", ["sub-a"])
        assert result == {}
