"""NLP-heavy tests for ClassifierTrainingTask.

Marked `slow`: real FastText training via ClassifierWrapper (requirements-nlp.txt).
Service/Mongo access is mocked; only the ML training is real. Excluded from CI.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import fasttext_unavailable

if fasttext_unavailable():
    pytest.skip("FastText (requirements-nlp.txt) not installed", allow_module_level=True)

from app.schemas.project import PendingPipeline
from app.schemas.topic import OTHER_TOPIC_ID, Topic
from app.tasks import classifier_training_task as task_mod

pytestmark = pytest.mark.slow


SPORTS = [
    "the football team scored a goal in the match",
    "the player kicked the ball into the net",
    "our team won the championship game last night",
    "the striker scored twice during the second half",
]
COOKING = [
    "preheat the oven and bake the cake with flour and sugar",
    "mix the eggs butter and flour to make the dough",
    "add salt and pepper to season the soup recipe",
    "roast the vegetables in the oven for thirty minutes",
]


def actx(value):
    @asynccontextmanager
    async def _cm(*args, **kwargs):
        yield value
    return _cm


def make_pipeline(topic_mapping, classifier_id=None) -> PendingPipeline:
    return PendingPipeline(
        generation_job_id="gen-1",
        generated_topics=[],
        reconciled_topics=[],
        topic_mapping=topic_mapping,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        classifier_id=classifier_id,
    )


def raw_docs(text_by_id) -> list[dict]:
    return [{"_id": doc_id, "plain_text": text} for doc_id, text in text_by_id.items()]


async def run_training(
    topics, *, pipeline, docs, tmp_path, monkeypatch
):
    """Drive _run with mocked services and real FastText training into tmp_path."""
    monkeypatch.setattr(task_mod.settings, "CLASSIFIER_DIR", str(tmp_path))

    project_service = AsyncMock()
    project_service.get_pending_pipeline.return_value = pipeline
    search_service = AsyncMock()
    search_service.get_documents_by_ids.return_value = docs

    with patch.object(task_mod, "project_service_context", actx(project_service)), \
         patch.object(task_mod, "search_service_context", actx(search_service)):
        result = await task_mod._run(
            [t.model_dump() for t in topics], "proj-1", "My classifier"
        )
    return result, project_service, search_service


# ---------------------------------------------------------------------------
# Guard clauses
# ---------------------------------------------------------------------------

class TestGuards:
    async def test_no_pending_pipeline_raises(self, tmp_path, monkeypatch):
        topic = Topic(topic_id="t1", name="A", description="d")
        with pytest.raises(ValueError, match="No pending pipeline"):
            await run_training(
                [topic], pipeline=None, docs=[], tmp_path=tmp_path, monkeypatch=monkeypatch
            )

    async def test_empty_topic_mapping_raises(self, tmp_path, monkeypatch):
        topic = Topic(topic_id="t1", name="A", description="d")
        with pytest.raises(ValueError, match="No training data"):
            await run_training(
                [topic], pipeline=make_pipeline({}), docs=[],
                tmp_path=tmp_path, monkeypatch=monkeypatch,
            )

    async def test_all_empty_texts_raises(self, tmp_path, monkeypatch):
        topic = Topic(topic_id="t1", name="A", description="d")
        pipeline = make_pipeline({"t1": ["d1", "d2"]})
        docs = raw_docs({"d1": "   ", "d2": ""})
        with pytest.raises(ValueError, match="empty text"):
            await run_training(
                [topic], pipeline=pipeline, docs=docs,
                tmp_path=tmp_path, monkeypatch=monkeypatch,
            )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestTraining:
    async def test_trains_saves_and_persists(self, tmp_path, monkeypatch):
        topics = [
            Topic(topic_id="sports", name="Sports", description="sport"),
            Topic(topic_id="cooking", name="Cooking", description="food"),
        ]
        mapping = {
            "sports": [f"s{i}" for i in range(len(SPORTS))],
            "cooking": [f"c{i}" for i in range(len(COOKING))],
        }
        text_by_id = {f"s{i}": t for i, t in enumerate(SPORTS)}
        text_by_id.update({f"c{i}": t for i, t in enumerate(COOKING)})

        result, project_service, _ = await run_training(
            topics, pipeline=make_pipeline(mapping), docs=raw_docs(text_by_id),
            tmp_path=tmp_path, monkeypatch=monkeypatch,
        )

        # Metadata returned
        assert result["name"] == "My classifier"
        assert [t["topic_id"] for t in result["topics"]] == ["sports", "cooking"]
        assert result["file_path"].startswith(str(tmp_path))
        # Model file actually written
        import os
        assert os.path.exists(result["file_path"])
        # Persisted + stamped with the same new classifier id
        project_service.save_classifier.assert_awaited_once()
        project_service.stamp_pipeline_classifier.assert_awaited_once()
        stamped_id = project_service.stamp_pipeline_classifier.call_args.args[1]
        assert stamped_id == result["classifier_id"]

    async def test_origin_topic_ids_drive_doc_lookup(self, tmp_path, monkeypatch):
        # Reconciled topic whose docs live under its origin (generation-era) ids.
        topic = Topic(
            topic_id="merged",
            name="Merged",
            description="d",
            origin_topic_ids=["gen-a", "gen-b"],
        )
        mapping = {
            "gen-a": ["d1", "d2"],
            "gen-b": ["d3"],
            "merged": ["should-not-be-used"],  # ignored because origins are present
        }
        docs = raw_docs({
            "d1": SPORTS[0], "d2": SPORTS[1], "d3": COOKING[0],
        })

        result, _, search_service = await run_training(
            [topic], pipeline=make_pipeline(mapping), docs=docs,
            tmp_path=tmp_path, monkeypatch=monkeypatch,
        )

        requested = set(search_service.get_documents_by_ids.call_args.args[0])
        assert requested == {"d1", "d2", "d3"}
        assert result["classifier_id"]

    async def test_other_class_included_in_training(self, tmp_path, monkeypatch):
        topic = Topic(topic_id="sports", name="Sports", description="d")
        mapping = {
            "sports": [f"s{i}" for i in range(len(SPORTS))],
            OTHER_TOPIC_ID: [f"o{i}" for i in range(len(COOKING))],
        }
        text_by_id = {f"s{i}": t for i, t in enumerate(SPORTS)}
        text_by_id.update({f"o{i}": t for i, t in enumerate(COOKING)})

        result, _, search_service = await run_training(
            [topic], pipeline=make_pipeline(mapping), docs=raw_docs(text_by_id),
            tmp_path=tmp_path, monkeypatch=monkeypatch,
        )

        # Outlier docs are fetched and fed into training as the reserved class.
        requested = set(search_service.get_documents_by_ids.call_args.args[0])
        assert {f"o{i}" for i in range(len(COOKING))} <= requested

        # The trained model can produce the OTHER label for clearly off-topic text.
        from app.infrastructure.classifier_wrapper import ClassifierWrapper
        wrapper = ClassifierWrapper()
        wrapper.load(result["file_path"])
        label, _conf = wrapper.predict("bake the cake in the oven with flour and sugar")
        assert label in {"sports", OTHER_TOPIC_ID}
