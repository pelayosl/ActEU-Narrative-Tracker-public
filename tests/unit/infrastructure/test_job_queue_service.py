from unittest.mock import Mock, patch

import pytest

from app.infrastructure.job_queue_service import JobQueueService
from app.schemas.jobs import JobStatus


@pytest.fixture
def service() -> JobQueueService:
    return JobQueueService(celery_app=Mock(), redis=Mock())


def fake_result(state, result=None, info=None) -> Mock:
    """Stand-in for a Celery AsyncResult."""
    r = Mock()
    r.state = state
    r.result = result
    r.info = info
    return r


# ---------------------------------------------------------------------------
# dispatch()
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_sends_named_task_and_returns_job_id(self):
        celery = Mock()
        celery.send_task.return_value = Mock(id="job-42")
        service = JobQueueService(celery_app=celery, redis=Mock())

        job_id = service.dispatch("app.tasks.some_task", {"a": 1})

        assert job_id == "job-42"
        celery.send_task.assert_called_once_with("app.tasks.some_task", kwargs={"a": 1})


# ---------------------------------------------------------------------------
# get_status() — Celery state → JobStatus mapping
# ---------------------------------------------------------------------------

class TestGetStatus:
    async def test_success_with_dict_result(self, service):
        with patch(
            "app.infrastructure.job_queue_service.AsyncResult",
            return_value=fake_result("SUCCESS", result={"total_labelled": 3}),
        ):
            status = await service.get_status("job-1")

        assert isinstance(status, JobStatus)
        assert status.job_id == "job-1"
        assert status.status == "SUCCESS"
        assert status.progress == 100
        assert status.result == {"total_labelled": 3}

    async def test_success_with_non_dict_result_is_wrapped(self, service):
        with patch(
            "app.infrastructure.job_queue_service.AsyncResult",
            return_value=fake_result("SUCCESS", result="done"),
        ):
            status = await service.get_status("job-1")

        assert status.progress == 100
        assert status.result == {"data": "done"}

    async def test_failure_maps_error_message(self, service):
        with patch(
            "app.infrastructure.job_queue_service.AsyncResult",
            return_value=fake_result("FAILURE", result=ValueError("boom")),
        ):
            status = await service.get_status("job-1")

        assert status.status == "FAILURE"
        assert status.progress == 0
        assert status.result == {"error": "boom"}

    async def test_progress_extracts_step_and_progress(self, service):
        with patch(
            "app.infrastructure.job_queue_service.AsyncResult",
            return_value=fake_result(
                "PROGRESS", info={"progress": 55, "step": "embedding"}
            ),
        ):
            status = await service.get_status("job-1")

        assert status.status == "PROGRESS"
        assert status.progress == 55
        assert status.result == {"step": "embedding"}

    async def test_progress_with_no_info_defaults(self, service):
        with patch(
            "app.infrastructure.job_queue_service.AsyncResult",
            return_value=fake_result("PROGRESS", info=None),
        ):
            status = await service.get_status("job-1")

        assert status.progress == 0
        assert status.result == {"step": ""}

    async def test_pending_state_is_neutral(self, service):
        with patch(
            "app.infrastructure.job_queue_service.AsyncResult",
            return_value=fake_result("PENDING"),
        ):
            status = await service.get_status("job-1")

        assert status.status == "PENDING"
        assert status.progress == 0
        assert status.result == {}
