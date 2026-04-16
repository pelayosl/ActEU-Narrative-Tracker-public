from collections.abc import AsyncGenerator

from celery import Celery
from redis.asyncio import Redis

from app.schemas.jobs import JobStatus


class JobQueueService:
    def __init__(self, celery_app: Celery, redis: Redis) -> None:
        self._celery = celery_app
        self._redis = redis

    def dispatch(self, task_name: str, kwargs: dict) -> str:
        raise NotImplementedError

    async def get_status(self, job_id: str) -> JobStatus:
        raise NotImplementedError

    async def stream_progress(self, job_id: str) -> AsyncGenerator[JobStatus, None]:
        raise NotImplementedError
