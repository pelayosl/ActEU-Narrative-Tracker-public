from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.exceptions import (
    ClassifierNotFound,
    NoPendingPipeline,
    PendingPipelineMismatch,
)
from app.schemas.classification import ClassifierMetadata
from app.schemas.project import PendingPipeline
from app.schemas.topic import Topic
from app.services.project_service import ProjectService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_topic(topic_id: str, *, origin_topic_ids: list[str] | None = None) -> Topic:
    return Topic(
        topic_id=topic_id,
        name=f"Topic {topic_id}",
        description=f"Description {topic_id}",
        origin_topic_ids=origin_topic_ids or [],
    )


def make_classifier(
    classifier_id: str = "clf-1",
    *,
    topics: list[Topic] | None = None,
) -> ClassifierMetadata:
    return ClassifierMetadata(
        classifier_id=classifier_id,
        name="My classifier",
        topics=topics if topics is not None else [make_topic("t1")],
        file_path=f"/classifiers/{classifier_id}.bin",
        created_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
    )


def make_pipeline(
    *,
    classifier_id: str | None = None,
    topic_mapping: dict[str, list[str]] | None = None,
) -> PendingPipeline:
    return PendingPipeline(
        generation_job_id="job-1",
        topic_mapping=topic_mapping if topic_mapping is not None else {"t1": ["doc-a"]},
        created_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        classifier_id=classifier_id,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def topic_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(project_repo, topic_repo) -> ProjectService:
    return ProjectService(project_repo, topic_repo)


# ---------------------------------------------------------------------------
# get_available_topics() — search-form facets from the DB
# ---------------------------------------------------------------------------

class TestGetAvailableTopics:
    async def test_splits_native_and_merges_project_subtopics(self, service, topic_repo, project_repo):
        topic_repo.find_all.return_value = [
            Topic(topic_id="u1", name="Immigration", description="", core_topic="immigration"),
            Topic(topic_id="u2", name="Gender Issues", description="", core_topic="gender_issues"),
            Topic(topic_id="s1", name="Asylum policy", description=""),  # db subtopic
            Topic(topic_id="s2", name="Women & sports", description=""),
        ]
        project_repo.find_all_classifiers.return_value = [
            make_classifier("c1", topics=[make_topic("p1")]),
        ]

        result = await service.get_available_topics("proj-1")

        # core topics submit their slug
        assert [(c.value, c.label) for c in result.core_topics] == [
            ("immigration", "Immigration"),
            ("gender_issues", "Gender Issues"),
        ]
        # subtopics = db ∪ project, sorted by label
        assert [(s.value, s.label) for s in result.subtopics] == [
            ("s1", "Asylum policy"),
            ("p1", "Topic p1"),
            ("s2", "Women & sports"),
        ]

    async def test_project_label_wins_on_topic_id_collision(self, service, topic_repo, project_repo):
        topic_repo.find_all.return_value = [
            Topic(topic_id="x", name="DB label", description=""),
        ]
        project_repo.find_all_classifiers.return_value = [
            make_classifier("c1", topics=[Topic(topic_id="x", name="Project label", description="")]),
        ]

        result = await service.get_available_topics("proj-1")

        assert [(s.value, s.label) for s in result.subtopics] == [("x", "Project label")]


# ---------------------------------------------------------------------------
# delete_classifier() — file removal + cascade delegation
# ---------------------------------------------------------------------------

class TestDeleteClassifier:
    async def test_not_found_raises(self, service, project_repo):
        project_repo.find_classifier.return_value = None

        with pytest.raises(ClassifierNotFound):
            await service.delete_classifier("proj-1", "clf-1")

        project_repo.delete_classifier.assert_not_awaited()

    async def test_removes_file_and_delegates(self, service, project_repo, tmp_path):
        bin_file = tmp_path / "clf-1.bin"
        bin_file.write_bytes(b"model")
        classifier = make_classifier("clf-1")
        classifier.file_path = str(bin_file)
        project_repo.find_classifier.return_value = classifier

        await service.delete_classifier("proj-1", "clf-1")

        assert not bin_file.exists()
        project_repo.delete_classifier.assert_awaited_once_with("proj-1", "clf-1")

    async def test_missing_file_is_tolerated(self, service, project_repo):
        # file_path points nowhere — deletion still proceeds at the DB level.
        project_repo.find_classifier.return_value = make_classifier("clf-1")

        await service.delete_classifier("proj-1", "clf-1")

        project_repo.delete_classifier.assert_awaited_once_with("proj-1", "clf-1")


# ---------------------------------------------------------------------------
# apply_pipeline_labels() — pipeline / classifier ownership guard
# ---------------------------------------------------------------------------

class TestApplyPipelineLabelsGuard:
    """The PendingPipelineMismatch condition: Phase 1 is only available when the
    pending pipeline's stamped classifier_id matches the classifier being applied."""

    async def test_no_pending_pipeline_raises(self, service, project_repo):
        project_repo.find_pending_pipeline.return_value = None

        with pytest.raises(NoPendingPipeline):
            await service.apply_pipeline_labels("proj-1", "clf-1")

    async def test_no_pending_pipeline_does_not_mutate(self, service, project_repo):
        project_repo.find_pending_pipeline.return_value = None

        with pytest.raises(NoPendingPipeline):
            await service.apply_pipeline_labels("proj-1", "clf-1")

        project_repo.upsert_document_proxies.assert_not_awaited()
        project_repo.clear_pending_pipeline.assert_not_awaited()

    async def test_classifier_not_found_raises(self, service, project_repo):
        project_repo.find_pending_pipeline.return_value = make_pipeline(classifier_id="clf-1")
        project_repo.find_classifier.return_value = None

        with pytest.raises(ClassifierNotFound):
            await service.apply_pipeline_labels("proj-1", "clf-1")

    async def test_unstamped_pipeline_raises_mismatch(self, service, project_repo):
        """classifier_id is None — training never completed for this pipeline run."""
        project_repo.find_pending_pipeline.return_value = make_pipeline(classifier_id=None)
        project_repo.find_classifier.return_value = make_classifier("clf-1")

        with pytest.raises(PendingPipelineMismatch):
            await service.apply_pipeline_labels("proj-1", "clf-1")

    async def test_overwritten_pipeline_raises_mismatch(self, service, project_repo):
        """A newer pipeline run stamped a different classifier_id."""
        project_repo.find_pending_pipeline.return_value = make_pipeline(classifier_id="clf-2")
        project_repo.find_classifier.return_value = make_classifier("clf-1")

        with pytest.raises(PendingPipelineMismatch):
            await service.apply_pipeline_labels("proj-1", "clf-1")

    async def test_mismatch_does_not_clear_pipeline(self, service, project_repo):
        """Critical: a mismatch must NOT clear the (newer) in-progress pipeline,
        nor write any proxies."""
        project_repo.find_pending_pipeline.return_value = make_pipeline(classifier_id="clf-2")
        project_repo.find_classifier.return_value = make_classifier("clf-1")

        with pytest.raises(PendingPipelineMismatch):
            await service.apply_pipeline_labels("proj-1", "clf-1")

        project_repo.clear_pending_pipeline.assert_not_awaited()
        project_repo.upsert_document_proxies.assert_not_awaited()


# ---------------------------------------------------------------------------
# apply_pipeline_labels() — happy path (matching classifier_id)
# ---------------------------------------------------------------------------

class TestApplyPipelineLabelsHappyPath:
    async def test_matching_classifier_id_proceeds(self, service, project_repo):
        project_repo.find_pending_pipeline.return_value = make_pipeline(
            classifier_id="clf-1", topic_mapping={"t1": ["doc-a", "doc-b"]}
        )
        project_repo.find_classifier.return_value = make_classifier(
            "clf-1", topics=[make_topic("t1")]
        )

        result = await service.apply_pipeline_labels("proj-1", "clf-1")

        assert result.project_id == "proj-1"
        assert result.total_labelled == 2
        assert result.topic_summary == {"t1": 2}

    async def test_upserts_proxies_then_clears_pipeline(self, service, project_repo):
        project_repo.find_pending_pipeline.return_value = make_pipeline(
            classifier_id="clf-1", topic_mapping={"t1": ["doc-a"]}
        )
        project_repo.find_classifier.return_value = make_classifier(
            "clf-1", topics=[make_topic("t1")]
        )

        await service.apply_pipeline_labels("proj-1", "clf-1")

        project_repo.upsert_document_proxies.assert_awaited_once()
        project_repo.clear_pending_pipeline.assert_awaited_once_with("proj-1")

    async def test_proxies_carry_phase_1_confidence(self, service, project_repo):
        """Phase 1 proxies are pure label assignment — no ML inference, confidence is assumed to be 1."""
        project_repo.find_pending_pipeline.return_value = make_pipeline(
            classifier_id="clf-1", topic_mapping={"t1": ["doc-a"]}
        )
        project_repo.find_classifier.return_value = make_classifier(
            "clf-1", topics=[make_topic("t1")]
        )

        await service.apply_pipeline_labels("proj-1", "clf-1")

        proxies = project_repo.upsert_document_proxies.await_args.args[1]
        assert proxies[0].labels[0].confidence == 1
        assert proxies[0].labels[0].classifier_id == "clf-1"

    async def test_reconciled_topic_resolves_via_origin_ids(self, service, project_repo):
        """A reconciled topic has its own topic_id but maps documents through
        origin_topic_ids (the generation-era keys in topic_mapping)."""
        project_repo.find_pending_pipeline.return_value = make_pipeline(
            classifier_id="clf-1",
            topic_mapping={"gen-a": ["doc-a"], "gen-b": ["doc-b"]},
        )
        reconciled = make_topic("recon-1", origin_topic_ids=["gen-a", "gen-b"])
        project_repo.find_classifier.return_value = make_classifier(
            "clf-1", topics=[reconciled]
        )

        result = await service.apply_pipeline_labels("proj-1", "clf-1")

        assert result.total_labelled == 2
        assert result.topic_summary == {"recon-1": 2}


# ---------------------------------------------------------------------------
# stamp_pipeline_classifier()
# ---------------------------------------------------------------------------

class TestStampPipelineClassifier:
    async def test_delegates_to_repo(self, service, project_repo):
        await service.stamp_pipeline_classifier("proj-1", "clf-1")
        project_repo.stamp_pipeline_classifier.assert_awaited_once_with("proj-1", "clf-1")
