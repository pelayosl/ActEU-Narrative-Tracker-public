"""Per-invocation dependency contexts for Celery tasks (no FastAPI DI here).

These context managers exist to own the lifecycle of the two networked backing
services — Mongo and Redis — that are opened from a settings URL and must be
closed in a `finally`. A dependency belongs here only if it holds such a
connection (e.g. MutexManager wraps a Redis client). Stateless helpers
(LLMClient) and local, self-closing resources (EmbeddingCache's SQLite file)
are instantiated directly in the task instead.
"""

from contextlib import asynccontextmanager

from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from app.config import settings
from app.infrastructure.mutex_manager import MutexManager
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.topic_repository import TopicRepository
from app.services.project_service import ProjectService
from app.services.search_service import SearchService


@asynccontextmanager
async def search_service_context():
    """Async context manager that creates a Motor client scoped to a single task invocation.
    Used by Celery tasks that need to call SearchService without FastAPI's DI."""
    client = AsyncMongoClient(settings.MONGODB_URL)
    try:
        db = client[settings.MONGODB_DB]
        yield SearchService(DocumentRepository(db))
    finally:
        await client.close()


@asynccontextmanager
async def project_service_context():
    """Async context manager for ProjectService, used by Celery tasks."""
    client = AsyncMongoClient(settings.MONGODB_URL)
    try:
        db = client[settings.MONGODB_DB]
        yield ProjectService(ProjectRepository(db), TopicRepository(db))
    finally:
        await client.close()


@asynccontextmanager
async def mutex_manager_context():
    """Async context manager for MutexManager, the only infrastructure class routed
    through a context, because it wraps a Redis connection that must be closed."""
    redis = Redis.from_url(settings.REDIS_URL)
    try:
        yield MutexManager(redis)
    finally:
        await redis.aclose()
