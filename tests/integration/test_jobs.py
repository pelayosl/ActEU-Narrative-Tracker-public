"""Integration test for the /jobs SSE stream.

The job queue is faked to yield a couple of JobStatus events so we verify the route wires
`stream_progress` into an SSE (`text/event-stream`) response without touching Redis/Celery.
"""

import pytest

from app.api import dependencies as deps
from app.schemas.jobs import JobStatus

pytestmark = pytest.mark.integration


class FakeJobQueue:
    async def stream_progress(self, job_id):
        yield JobStatus(job_id=job_id, status="STARTED", progress=0)
        yield JobStatus(job_id=job_id, status="SUCCESS", progress=100, result={"ok": True})


class TestStreamJob:
    async def test_streams_sse_events(self, override, client):
        override(deps.get_job_queue, FakeJobQueue)

        res = await client.get("/jobs/job-1/stream")

        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        assert "STARTED" in res.text
        assert "SUCCESS" in res.text
