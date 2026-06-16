from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.schemas.topic import Topic
from app.tasks import reconciliation_task as task_mod


def actx(value):
    """Build an async-context-manager factory that yields `value`."""
    @asynccontextmanager
    async def _cm(*args, **kwargs):
        yield value
    return _cm


def make_topic(topic_id="t1", name="A", description="d") -> Topic:
    return Topic(topic_id=topic_id, name=name, description=description)


# ---------------------------------------------------------------------------
# _run() — reconciliation orchestration
# ---------------------------------------------------------------------------

class TestReconciliationRun:
    async def test_persists_and_returns_reconciled_topics_when_llm_available(self):
        reconciled = [make_topic(topic_id="merged", name="Merged")]
        llm = Mock()
        llm.reconcile.return_value = (reconciled, True)
        project_service = AsyncMock()

        with patch.object(task_mod, "LLMClient", return_value=llm), patch.object(
            task_mod, "project_service_context", actx(project_service)
        ):
            result = await task_mod._run(
                "proj-1", [make_topic(topic_id="t1").model_dump()]
            )

        assert result["llm_available"] is True
        assert [t["topic_id"] for t in result["topics"]] == ["merged"]
        project_service.update_reconciled_topics.assert_awaited_once()
        # The persisted topics are the reconciled ones.
        persisted = project_service.update_reconciled_topics.call_args.args[1]
        assert [t.topic_id for t in persisted] == ["merged"]

    async def test_does_not_persist_when_llm_unavailable(self):
        llm = Mock()
        # Fallback contract: unchanged input + llm_available False.
        llm.reconcile.return_value = ([make_topic()], False)
        project_service = AsyncMock()

        with patch.object(task_mod, "LLMClient", return_value=llm), patch.object(
            task_mod, "project_service_context", actx(project_service)
        ):
            result = await task_mod._run("proj-1", [make_topic().model_dump()])

        assert result["llm_available"] is False
        assert result["topics"] == []
        project_service.update_reconciled_topics.assert_not_awaited()

    async def test_parses_incoming_dicts_into_topic_objects(self):
        llm = Mock()
        llm.reconcile.return_value = ([], True)
        project_service = AsyncMock()

        with patch.object(task_mod, "LLMClient", return_value=llm), patch.object(
            task_mod, "project_service_context", actx(project_service)
        ):
            await task_mod._run(
                "proj-1",
                [{"topic_id": "t1", "name": "A", "description": "d"}],
            )

        passed = llm.reconcile.call_args.args[0]
        assert all(isinstance(t, Topic) for t in passed)
        assert passed[0].topic_id == "t1"
