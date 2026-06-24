from datetime import datetime

import pytest

from app.repositories.project_repository import ProjectRepository
from app.schemas.classification import ClassifierMetadata, DocumentProxy, ProxyLabel
from app.schemas.project import PendingPipeline, Project
from app.schemas.topic import Topic

CREATED = datetime(2024, 1, 1)


@pytest.fixture
async def repo(db):
    return ProjectRepository(db)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def make_project(project_id="p1", owner_id="u1", **overrides) -> Project:
    base = dict(project_id=project_id, owner_id=owner_id, name="P", created_at=CREATED)
    base.update(overrides)
    return Project(**base)


def make_topic(topic_id="t1", name="Topic") -> Topic:
    return Topic(topic_id=topic_id, name=name, description="")


def make_classifier(classifier_id="c1", name="C", topics=None) -> ClassifierMetadata:
    return ClassifierMetadata(
        classifier_id=classifier_id,
        name=name,
        topics=topics or [],
        file_path=f"/models/{classifier_id}.bin",
        created_at=CREATED,
    )


def make_label(topic_id="sub-a", name="Wind", classifier_id="c1", confidence=0.9) -> ProxyLabel:
    return ProxyLabel(
        topic_id=topic_id,
        name=name,
        description="",
        classifier_id=classifier_id,
        confidence=confidence,
    )


def make_proxy(doc_id="d1", labels=None) -> DocumentProxy:
    return DocumentProxy(doc_id=doc_id, labels=labels or [make_label()])


def make_pipeline(generation_job_id="g1", **overrides) -> PendingPipeline:
    base = dict(generation_job_id=generation_job_id, created_at=CREATED)
    base.update(overrides)
    return PendingPipeline(**base)


# ---------------------------------------------------------------------------
# save / find_by_id / find_by_owner / delete
# ---------------------------------------------------------------------------

class TestSaveAndFind:
    async def test_save_inserts_and_find_by_id_returns_project(self, repo):
        await repo.save(make_project("p1", name="Energy"))
        found = await repo.find_by_id("p1")
        assert found is not None
        assert found.project_id == "p1"
        assert found.name == "Energy"

    async def test_find_by_id_unknown_returns_none(self, repo):
        assert await repo.find_by_id("nope") is None

    async def test_save_upserts_by_project_id(self, repo):
        await repo.save(make_project("p1", name="Old"))
        await repo.save(make_project("p1", name="New"))
        found = await repo.find_by_id("p1")
        assert found.name == "New"

    async def test_save_does_not_duplicate(self, db, repo):
        await repo.save(make_project("p1"))
        await repo.save(make_project("p1"))
        assert await db["projects"].count_documents({"project_id": "p1"}) == 1

    async def test_find_by_owner_returns_only_owned(self, repo):
        await repo.save(make_project("p1", owner_id="alice"))
        await repo.save(make_project("p2", owner_id="alice"))
        await repo.save(make_project("p3", owner_id="bob"))
        owned = await repo.find_by_owner("alice")
        assert {p.project_id for p in owned} == {"p1", "p2"}

    async def test_find_by_owner_none_returns_empty(self, repo):
        assert await repo.find_by_owner("ghost") == []

    async def test_delete_removes_project(self, repo):
        await repo.save(make_project("p1"))
        await repo.delete("p1")
        assert await repo.find_by_id("p1") is None

    async def test_delete_unknown_is_noop(self, repo):
        await repo.delete("nope")  # must not raise


# ---------------------------------------------------------------------------
# Classifiers
# ---------------------------------------------------------------------------

class TestClassifiers:
    async def test_add_and_find_classifier(self, repo):
        await repo.save(make_project("p1"))
        await repo.add_classifier("p1", make_classifier("c1", name="First"))
        found = await repo.find_classifier("p1", "c1")
        assert found is not None
        assert found.classifier_id == "c1"
        assert found.name == "First"

    async def test_find_classifier_unknown_returns_none(self, repo):
        await repo.save(make_project("p1"))
        await repo.add_classifier("p1", make_classifier("c1"))
        assert await repo.find_classifier("p1", "c2") is None

    async def test_find_all_classifiers(self, repo):
        await repo.save(make_project("p1"))
        await repo.add_classifier("p1", make_classifier("c1"))
        await repo.add_classifier("p1", make_classifier("c2"))
        all_classifiers = await repo.find_all_classifiers("p1")
        assert {c.classifier_id for c in all_classifiers} == {"c1", "c2"}

    async def test_find_all_classifiers_empty(self, repo):
        await repo.save(make_project("p1"))
        assert await repo.find_all_classifiers("p1") == []

    async def test_delete_classifier_removes_metadata(self, repo):
        await repo.save(make_project("p1"))
        await repo.add_classifier("p1", make_classifier("c1"))
        await repo.add_classifier("p1", make_classifier("c2"))
        await repo.delete_classifier("p1", "c1")
        remaining = await repo.find_all_classifiers("p1")
        assert {c.classifier_id for c in remaining} == {"c2"}

    async def test_delete_classifier_cascades_labels_and_prunes_empty_proxies(self, repo):
        # d1 only carries a c1 label (becomes empty → pruned); d2 carries c1 + c2
        # (keeps c2). Mirrors the cascade described in the repository.
        project = make_project(
            "p1",
            classifiers=[make_classifier("c1"), make_classifier("c2")],
            document_proxies=[
                make_proxy("d1", [make_label(topic_id="sub-a", classifier_id="c1")]),
                make_proxy(
                    "d2",
                    [
                        make_label(topic_id="sub-a", classifier_id="c1"),
                        make_label(topic_id="sub-b", classifier_id="c2"),
                    ],
                ),
            ],
        )
        await repo.save(project)

        await repo.delete_classifier("p1", "c1")

        found = await repo.find_by_id("p1")
        proxy_ids = {p.doc_id for p in found.document_proxies}
        assert proxy_ids == {"d2"}  # d1 pruned, d2 survives
        d2 = next(p for p in found.document_proxies if p.doc_id == "d2")
        assert [lbl.classifier_id for lbl in d2.labels] == ["c2"]


# ---------------------------------------------------------------------------
# Document proxies
# ---------------------------------------------------------------------------

class TestDocumentProxies:
    async def test_upsert_adds_new_proxy(self, repo):
        await repo.save(make_project("p1"))
        await repo.upsert_document_proxies(
            "p1", [make_proxy("d1", [make_label(topic_id="sub-a")])]
        )
        found = await repo.find_by_id("p1")
        assert [p.doc_id for p in found.document_proxies] == ["d1"]
        assert found.document_proxies[0].labels[0].topic_id == "sub-a"

    async def test_upsert_appends_label_to_existing_proxy(self, repo):
        await repo.save(make_project("p1"))
        await repo.upsert_document_proxies(
            "p1", [make_proxy("d1", [make_label(topic_id="sub-a")])]
        )
        await repo.upsert_document_proxies(
            "p1", [make_proxy("d1", [make_label(topic_id="sub-b")])]
        )
        found = await repo.find_by_id("p1")
        assert len(found.document_proxies) == 1
        topic_ids = {lbl.topic_id for lbl in found.document_proxies[0].labels}
        assert topic_ids == {"sub-a", "sub-b"}

    async def test_upsert_does_not_duplicate_same_label(self, repo):
        await repo.save(make_project("p1"))
        label = make_label(topic_id="sub-a", classifier_id="c1")
        await repo.upsert_document_proxies("p1", [make_proxy("d1", [label])])
        await repo.upsert_document_proxies("p1", [make_proxy("d1", [label])])
        found = await repo.find_by_id("p1")
        assert len(found.document_proxies) == 1
        assert len(found.document_proxies[0].labels) == 1

    async def test_filter_by_subtopics_returns_matching_names(self, repo):
        project = make_project(
            "p1",
            document_proxies=[
                make_proxy("d1", [make_label(topic_id="sub-a", name="Wind")]),
                make_proxy("d2", [make_label(topic_id="sub-b", name="Solar")]),
            ],
        )
        await repo.save(project)
        result = await repo.filter_proxy_doc_ids_by_subtopics("p1", ["sub-a"])
        assert result == {"d1": ["Wind"]}

    async def test_filter_by_subtopics_applies_confidence_threshold(self, repo):
        project = make_project(
            "p1",
            document_proxies=[
                make_proxy("d1", [make_label(topic_id="sub-a", name="Wind", confidence=0.5)]),
            ],
        )
        await repo.save(project)
        assert await repo.filter_proxy_doc_ids_by_subtopics("p1", ["sub-a"], 0.9) == {}
        assert await repo.filter_proxy_doc_ids_by_subtopics("p1", ["sub-a"], 0.4) == {"d1": ["Wind"]}

    async def test_filter_by_subtopics_unknown_project_empty(self, repo):
        assert await repo.filter_proxy_doc_ids_by_subtopics("nope", ["sub-a"]) == {}

    async def test_find_labelled_doc_ids(self, repo):
        project = make_project(
            "p1",
            document_proxies=[
                make_proxy("d1", [make_label(classifier_id="c1")]),
                make_proxy("d2", [make_label(classifier_id="c2")]),
                make_proxy(
                    "d3",
                    [make_label(classifier_id="c1"), make_label(topic_id="sub-b", classifier_id="c2")],
                ),
            ],
        )
        await repo.save(project)
        assert set(await repo.find_labelled_doc_ids("p1", "c1")) == {"d1", "d3"}

    async def test_find_labelled_doc_ids_unknown_project_empty(self, repo):
        assert await repo.find_labelled_doc_ids("nope", "c1") == []


# ---------------------------------------------------------------------------
# find_proxy_confidence_by_topics
# ---------------------------------------------------------------------------

class TestFindProxyConfidenceByTopics:
    async def test_matches_by_topic_id(self, repo):
        await repo.save(make_project("p1", document_proxies=[
            make_proxy("d1", [make_label(topic_id="sub-a", name="Wind energy", confidence=0.75)]),
            make_proxy("d2", [make_label(topic_id="sub-b", name="Solar energy", confidence=0.6)]),
        ]))
        result = await repo.find_proxy_confidence_by_topics("p1", ["sub-a"])
        assert result == {"sub-a": {"d1": 0.75}}

    async def test_does_not_match_by_name(self, repo):
        await repo.save(make_project("p1", document_proxies=[
            make_proxy("d1", [make_label(topic_id="sub-a", name="Wind energy")]),
        ]))
        result = await repo.find_proxy_confidence_by_topics("p1", ["Wind energy"])
        assert result == {}

    async def test_multiple_docs_per_topic(self, repo):
        await repo.save(make_project("p1", document_proxies=[
            make_proxy("d1", [make_label(topic_id="sub-a", name="Wind energy", confidence=0.8)]),
            make_proxy("d2", [make_label(topic_id="sub-a", name="Wind energy", confidence=0.4)]),
        ]))
        result = await repo.find_proxy_confidence_by_topics("p1", ["sub-a"])
        assert result["sub-a"] == {"d1": 0.8, "d2": 0.4}

    async def test_omits_topics_without_match(self, repo):
        await repo.save(make_project("p1", document_proxies=[
            make_proxy("d1", [make_label(topic_id="sub-a", name="Wind energy", confidence=0.5)]),
        ]))
        result = await repo.find_proxy_confidence_by_topics("p1", ["sub-a", "sub-z"])
        assert "sub-z" not in result
        assert result == {"sub-a": {"d1": 0.5}}

    async def test_unknown_project_returns_empty(self, repo):
        assert await repo.find_proxy_confidence_by_topics("nope", ["sub-a"]) == {}

    async def test_no_proxies_returns_empty(self, repo):
        await repo.save(make_project("p1", document_proxies=[]))
        assert await repo.find_proxy_confidence_by_topics("p1", ["sub-a"]) == {}


# ---------------------------------------------------------------------------
# Pending pipeline
# ---------------------------------------------------------------------------

class TestPendingPipeline:
    async def test_set_and_find_pipeline(self, repo):
        await repo.save(make_project("p1"))
        await repo.set_pending_pipeline("p1", make_pipeline("job-1"))
        found = await repo.find_pending_pipeline("p1")
        assert found is not None
        assert found.generation_job_id == "job-1"

    async def test_find_pipeline_none_when_absent(self, repo):
        await repo.save(make_project("p1"))
        assert await repo.find_pending_pipeline("p1") is None

    async def test_clear_pending_pipeline(self, repo):
        await repo.save(make_project("p1"))
        await repo.set_pending_pipeline("p1", make_pipeline("job-1"))
        await repo.clear_pending_pipeline("p1")
        assert await repo.find_pending_pipeline("p1") is None

    async def test_stamp_pipeline_classifier(self, repo):
        await repo.save(make_project("p1"))
        await repo.set_pending_pipeline("p1", make_pipeline("job-1"))
        await repo.stamp_pipeline_classifier("p1", "c1")
        found = await repo.find_pending_pipeline("p1")
        assert found.classifier_id == "c1"

    async def test_update_reconciled_topics(self, repo):
        await repo.save(make_project("p1"))
        await repo.set_pending_pipeline("p1", make_pipeline("job-1"))
        await repo.update_reconciled_topics(
            "p1", [make_topic("t1", "Wind"), make_topic("t2", "Solar")]
        )
        found = await repo.find_pending_pipeline("p1")
        assert [t.topic_id for t in found.reconciled_topics] == ["t1", "t2"]
