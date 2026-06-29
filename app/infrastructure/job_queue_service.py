import asyncio
from collections.abc import AsyncGenerator

from celery import Celery
from celery.result import AsyncResult
from redis.asyncio import Redis

from app.infrastructure.timing import log_timing
from app.schemas.jobs import JobStatus

_TERMINAL_STATES = {"SUCCESS", "FAILURE", "REVOKED"}
_POLL_INTERVAL = 1.0  # seconds


class JobQueueService:
    """Infrastructure facade over Celery and Redis for background jobs.

    Dispatches tasks and reads their state from Redis. It has no MongoDB or repository
    dependency, the job state lives entirely in the Celery result backend.
    """

    def __init__(self, celery_app: Celery, redis: Redis) -> None:
        """Store the Celery application and Redis client this service uses.

        :param celery_app: The configured Celery application.
        :param redis: An async Redis client (the Celery result backend store).
        """
        self._celery = celery_app
        self._redis = redis

    def dispatch(self, task_name: str, kwargs: dict) -> str:
        """Enqueue a named Celery task and return its job_id.

        :param task_name: The dotted task name to send.
        :param kwargs: Keyword arguments passed to the task.
        :returns: The dispatched task's id.
        """
        async_result = self._celery.send_task(task_name, kwargs=kwargs)
        # Timing : record the dispatch instant so the parser can pair it with
        # the worker's task-start time (by job_id) and derive queue-wait latency.
        log_timing(task_name, event="dispatch", job_id=async_result.id)
        return async_result.id

    async def get_status(self, job_id: str) -> JobStatus:
        """Read the current Celery task state from Redis without blocking.

        The synchronous Celery lookup runs in a worker thread so it does not block the
        event loop.

        :param job_id: The job to inspect.
        :returns: A :class:`JobStatus` snapshot with state, progress and any result.
        """
        def _fetch() -> JobStatus:
            result = AsyncResult(job_id, app=self._celery)
            state = result.state
            task_result: dict = {}
            progress: int = 0

            if state == "SUCCESS":
                raw = result.result
                task_result = raw if isinstance(raw, dict) else {"data": raw}
                progress = 100
            elif state == "FAILURE":
                task_result = {"error": str(result.result)}
                progress = 0
            elif state == "PROGRESS":
                info = result.info or {}
                progress = info.get("progress", 0)
                task_result = {"step": info.get("step", "")}

            return JobStatus(job_id=job_id, status=state, progress=progress, result=task_result)

        return await asyncio.to_thread(_fetch)

    async def stream_progress(self, job_id: str) -> AsyncGenerator[JobStatus, None]:
        """Yield JobStatus events until the task reaches a terminal state.

        Polls the task state every ``_POLL_INTERVAL`` seconds, emitting one status per
        poll, and stops after the first terminal state (SUCCESS, FAILURE or REVOKED).

        :param job_id: The job to stream.
        :returns: An async generator of :class:`JobStatus` snapshots.
        """
        while True:
            job_status = await self.get_status(job_id)
            yield job_status
            if job_status.status in _TERMINAL_STATES:
                break
            await asyncio.sleep(_POLL_INTERVAL)
