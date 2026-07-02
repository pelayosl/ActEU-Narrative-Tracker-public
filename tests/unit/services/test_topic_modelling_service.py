from unittest.mock import Mock

import pytest

from app.infrastructure.job_queue_service import JobQueueService
from app.services.topic_modelling_service import TopicModellingService

GENERATION_TASK = "app.tasks.topic_generation_task.topic_generation_task"
RECONCILIATION_TASK = "app.tasks.reconciliation_task.reconciliation_task"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def job_queue() -> Mock:
    # dispatch() is synchronous and returns a job_id string.
    queue = Mock(spec=JobQueueService)
    queue.dispatch.return_value = "job-123"
    return queue


@pytest.fixture
def service(job_queue) -> TopicModellingService:
    return TopicModellingService(job_queue)


# ---------------------------------------------------------------------------
# submit_generation()
# ---------------------------------------------------------------------------

class TestSubmitGeneration:
    async def test_dispatches_generation_task(self, service, job_queue):
        service.submit_generation("proj-1", ["d1", "d2"])

        task_name = job_queue.dispatch.call_args.args[0]
        assert task_name == GENERATION_TASK

    async def test_returns_dispatched_job_id(self, service, job_queue):
        job_queue.dispatch.return_value = "gen-job-1"

        job_id = service.submit_generation("proj-1", ["d1"])

        assert job_id == "gen-job-1"

    async def test_payload_carries_project_and_doc_ids(self, service, job_queue):
        service.submit_generation("proj-1", ["d1", "d2", "d3"])

        kwargs = job_queue.dispatch.call_args.args[1]
        assert kwargs["project_id"] == "proj-1"
        assert kwargs["doc_ids"] == ["d1", "d2", "d3"]

    async def test_empty_doc_ids_is_allowed(self, service, job_queue):
        service.submit_generation("proj-1", [])

        assert job_queue.dispatch.call_args.args[1]["doc_ids"] == []


# ---------------------------------------------------------------------------
# submit_reconciliation()
# ---------------------------------------------------------------------------

class TestSubmitReconciliation:
    async def test_dispatches_reconciliation_task(self, service, job_queue):
        service.submit_reconciliation("proj-1", [])

        task_name = job_queue.dispatch.call_args.args[0]
        assert task_name == RECONCILIATION_TASK

    async def test_returns_dispatched_job_id(self, service, job_queue):
        job_queue.dispatch.return_value = "rec-job-1"

        job_id = service.submit_reconciliation("proj-1", [])

        assert job_id == "rec-job-1"

    async def test_payload_carries_project_and_topics(self, service, job_queue):
        topics = [
            {"topic_id": "t1", "name": "A", "description": "da"},
            {"topic_id": "t2", "name": "B", "description": "db"},
        ]

        service.submit_reconciliation("proj-1", topics)

        kwargs = job_queue.dispatch.call_args.args[1]
        assert kwargs["project_id"] == "proj-1"
        assert kwargs["topics"] == topics

    async def test_empty_topics_is_allowed(self, service, job_queue):
        service.submit_reconciliation("proj-1", [])

        assert job_queue.dispatch.call_args.args[1]["topics"] == []
