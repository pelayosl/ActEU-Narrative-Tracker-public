import asyncio
from collections.abc import AsyncGenerator

from celery import Celery
from celery.result import AsyncResult
from redis.asyncio import Redis

from app.schemas.jobs import JobStatus

_TERMINAL_STATES = {"SUCCESS", "FAILURE", "REVOKED"}
_POLL_INTERVAL = 1.0  # seconds


class JobQueueService:
    def __init__(self, celery_app: Celery, redis: Redis) -> None:
        self._celery = celery_app
        self._redis = redis

    def dispatch(self, task_name: str, kwargs: dict) -> str:
        """Enqueue a named Celery task and return its job_id."""
        async_result = self._celery.send_task(task_name, kwargs=kwargs)
        return async_result.id

    async def get_status(self, job_id: str) -> JobStatus:
        """Read the current Celery task state from Redis (non-blocking)."""
        def _fetch() -> JobStatus:
            result = AsyncResult(job_id, app=self._celery)
            state = result.state
            task_result: dict = {}
            if state == "SUCCESS":
                raw = result.result
                # Tasks may return a list - wrap so JobStatus.result stays a dict
                task_result = raw if isinstance(raw, dict) else {"data": raw}
            elif state == "FAILURE":
                task_result = {"error": str(result.result)}
            progress = 100 if state in _TERMINAL_STATES else 0
            return JobStatus(job_id=job_id, status=state, progress=progress, result=task_result)

        return await asyncio.to_thread(_fetch)

    async def stream_progress(self, job_id: str) -> AsyncGenerator[JobStatus, None]:
        """Yield JobStatus events until the task reaches a terminal state."""
        while True:
            job_status = await self.get_status(job_id)
            yield job_status
            if job_status.status in _TERMINAL_STATES:
                break
            await asyncio.sleep(_POLL_INTERVAL)
