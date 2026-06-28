"""Per-invocation dependency contexts for Celery tasks (no FastAPI DI here).

These context managers exist to own the lifecycle of the two networked backing
services, Mongo and Redis, that are opened from a settings URL and must be
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
    """Provide a SearchService backed by a per-invocation Mongo client.

    Used by Celery tasks that need ``SearchService`` without FastAPI's DI, closing the
    client when the context exits.

    :yields: A :class:`SearchService` valid for the duration of the context.
    """
    client = AsyncMongoClient(settings.MONGODB_URL)
    try:
        db = client[settings.MONGODB_DB]
        yield SearchService(DocumentRepository(db))
    finally:
        await client.close()


@asynccontextmanager
async def project_service_context():
    """Provide a ProjectService backed by a per-invocation Mongo client.

    Used by Celery tasks that need ``ProjectService`` without FastAPI's DI, closing the
    client when the context exits.

    :yields: A :class:`ProjectService` valid for the duration of the context.
    """
    client = AsyncMongoClient(settings.MONGODB_URL)
    try:
        db = client[settings.MONGODB_DB]
        yield ProjectService(ProjectRepository(db), TopicRepository(db))
    finally:
        await client.close()


@asynccontextmanager
async def mutex_manager_context():
    """Provide a MutexManager backed by a per-invocation Redis client.

    This is the only infrastructure class routed through a context, because it wraps a
    Redis connection that must be closed when the context exits.

    :yields: A :class:`MutexManager` valid for the duration of the context.
    """
    redis = Redis.from_url(settings.REDIS_URL)
    try:
        yield MutexManager(redis)
    finally:
        await redis.aclose()
