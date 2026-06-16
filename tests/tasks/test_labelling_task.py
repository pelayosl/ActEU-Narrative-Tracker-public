import sys
import types
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

# FastText is an NLP-only dependency (requirements-nlp.txt) absent from the CI/dev
# environment, but `labelling_task` imports ClassifierWrapper at module load. The
# wrapper is fully mocked in these tests, so a bare stub is enough to import.
sys.modules.setdefault("fasttext", types.ModuleType("fasttext"))

from app.exceptions import LabellingLocked
from app.schemas.classification import ClassifierMetadata
from app.schemas.search import DocumentSummary, SearchResult
from app.schemas.topic import OTHER_TOPIC_ID, Topic
from app.tasks import labelling_task as task_mod


def actx(value):
    """Build an async-context-manager factory that yields `value`."""
    @asynccontextmanager
    async def _cm(*args, **kwargs):
        yield value
    return _cm


def make_classifier(topics=None) -> ClassifierMetadata:
    return ClassifierMetadata(
        classifier_id="clf-1",
        name="My classifier",
        topics=topics if topics is not None else [
            Topic(topic_id="t1", name="Immigration", description="imm"),
            Topic(topic_id="t2", name="Climate", description="cli"),
        ],
        file_path="/models/clf-1.bin",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def make_search_result(doc_ids) -> SearchResult:
    docs = [
        DocumentSummary(
            doc_id=d, headline="", excerpt="", platform="twitter", language="en"
        )
        for d in doc_ids
    ]
    return SearchResult(total_docs=len(docs), retrieved_docs=docs)


def raw_doc(doc_id, text="some text") -> dict:
    return {"_id": doc_id, "plain_text": text}


def build_mocks(
    *,
    acquire=True,
    classifier=None,
    already_labelled=None,
    search_ids=("d1",),
    docs=None,
    predictions=None,
):
    """Wire up the three service mocks and the ClassifierWrapper used by _run."""
    mutex = AsyncMock()
    mutex.acquire.return_value = acquire

    project_service = AsyncMock()
    project_service.get_classifier.return_value = classifier or make_classifier()
    project_service.get_labelled_doc_ids.return_value = set(already_labelled or set())

    search_service = AsyncMock()
    search_service.search.return_value = make_search_result(list(search_ids))
    search_service.get_documents_by_ids.return_value = docs if docs is not None else [
        raw_doc(d) for d in search_ids
    ]

    wrapper = Mock()
    # predictions: dict text -> (topic_id, confidence); default predicts t1@0.9
    def _predict(text):
        if predictions is not None:
            return predictions[text]
        return ("t1", 0.9)
    wrapper.predict.side_effect = _predict

    return mutex, project_service, search_service, wrapper


def patches(mutex, project_service, search_service, wrapper):
    return (
        patch.object(task_mod, "mutex_manager_context", actx(mutex)),
        patch.object(task_mod, "project_service_context", actx(project_service)),
        patch.object(task_mod, "search_service_context", actx(search_service)),
        patch.object(task_mod, "ClassifierWrapper", return_value=wrapper),
    )


async def run_label(mutex, project_service, search_service, wrapper, query=None):
    p1, p2, p3, p4 = patches(mutex, project_service, search_service, wrapper)
    with p1, p2, p3, p4:
        return await task_mod._run("proj-1", "clf-1", query or {})


# ---------------------------------------------------------------------------
# Mutex behaviour
# ---------------------------------------------------------------------------

class TestMutex:
    async def test_rejects_when_lock_already_held(self):
        mutex, ps, ss, wrapper = build_mocks(acquire=False)

        with pytest.raises(LabellingLocked):
            await run_label(mutex, ps, ss, wrapper)

        # Never proceeded to do work.
        ps.get_classifier.assert_not_awaited()
        mutex.release.assert_not_awaited()

    async def test_lock_released_on_success(self):
        mutex, ps, ss, wrapper = build_mocks()

        await run_label(mutex, ps, ss, wrapper)

        mutex.acquire.assert_awaited_once()
        mutex.release.assert_awaited_once()

    async def test_lock_released_on_failure(self):
        mutex, ps, ss, wrapper = build_mocks()
        ps.get_classifier.side_effect = RuntimeError("db down")

        with pytest.raises(RuntimeError):
            await run_label(mutex, ps, ss, wrapper)

        mutex.release.assert_awaited_once()


# ---------------------------------------------------------------------------
# Labelling logic
# ---------------------------------------------------------------------------

class TestLabelling:
    async def test_labels_predicted_documents(self):
        mutex, ps, ss, wrapper = build_mocks(
            search_ids=("d1", "d2"),
            docs=[raw_doc("d1"), raw_doc("d2")],
            predictions={"some text": ("t1", 0.9)},
        )

        result = await run_label(mutex, ps, ss, wrapper)

        assert result["total_labelled"] == 2
        assert result["topic_summary"] == {"t1": 2}
        ps.upsert_document_proxies.assert_awaited_once()
        proxies = ps.upsert_document_proxies.call_args.args[1]
        assert {p.doc_id for p in proxies} == {"d1", "d2"}
        label = proxies[0].labels[0]
        assert label.topic_id == "t1"
        assert label.name == "Immigration"
        assert label.classifier_id == "clf-1"
        assert label.confidence == 0.9

    async def test_already_labelled_docs_are_filtered_out(self):
        mutex, ps, ss, wrapper = build_mocks(
            search_ids=("d1", "d2"),
            already_labelled={"d1"},
            docs=[raw_doc("d2")],
        )

        result = await run_label(mutex, ps, ss, wrapper)

        # Only the not-yet-labelled candidate is fetched.
        ss.get_documents_by_ids.assert_awaited_once_with(["d2"])
        assert result["total_labelled"] == 1

    async def test_other_predictions_are_not_labelled(self):
        mutex, ps, ss, wrapper = build_mocks(
            search_ids=("d1",),
            docs=[raw_doc("d1")],
            predictions={"some text": (OTHER_TOPIC_ID, 0.95)},
        )

        result = await run_label(mutex, ps, ss, wrapper)

        assert result["total_labelled"] == 0
        assert result["topic_summary"] == {}
        ps.upsert_document_proxies.assert_not_awaited()

    async def test_prediction_for_unknown_topic_is_skipped(self):
        mutex, ps, ss, wrapper = build_mocks(
            search_ids=("d1",),
            docs=[raw_doc("d1")],
            predictions={"some text": ("ghost-topic", 0.8)},
        )

        result = await run_label(mutex, ps, ss, wrapper)

        assert result["total_labelled"] == 0
        ps.upsert_document_proxies.assert_not_awaited()

    async def test_blank_text_documents_are_skipped(self):
        mutex, ps, ss, wrapper = build_mocks(
            search_ids=("d1",),
            docs=[raw_doc("d1", text="   ")],
        )

        result = await run_label(mutex, ps, ss, wrapper)

        assert result["total_labelled"] == 0
        wrapper.predict.assert_not_called()

    async def test_no_candidates_returns_empty_without_loading_docs(self):
        mutex, ps, ss, wrapper = build_mocks(
            search_ids=("d1",), already_labelled={"d1"}
        )

        result = await run_label(mutex, ps, ss, wrapper)

        assert result["total_labelled"] == 0
        assert result["topic_summary"] == {}
        ss.get_documents_by_ids.assert_not_awaited()
        ps.upsert_document_proxies.assert_not_awaited()

    async def test_classifier_model_is_loaded_from_file_path(self):
        mutex, ps, ss, wrapper = build_mocks()

        await run_label(mutex, ps, ss, wrapper)

        wrapper.load.assert_called_once_with("/models/clf-1.bin")

    async def test_topic_summary_counts_per_topic(self):
        mutex, ps, ss, wrapper = build_mocks(
            search_ids=("d1", "d2", "d3"),
            docs=[raw_doc("d1", "a"), raw_doc("d2", "b"), raw_doc("d3", "c")],
            predictions={"a": ("t1", 0.9), "b": ("t1", 0.7), "c": ("t2", 0.8)},
        )

        result = await run_label(mutex, ps, ss, wrapper)

        assert result["total_labelled"] == 3
        assert result["topic_summary"] == {"t1": 2, "t2": 1}
