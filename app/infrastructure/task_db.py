from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.repositories.document_repository import DocumentRepository
from app.services.search_service import SearchService


@asynccontextmanager
async def search_service_context():
    """Async context manager that creates a Motor client scoped to a single task invocation.
    Used by Celery tasks that need to call SearchService without FastAPI's DI."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    try:
        db = client[settings.MONGODB_DB]
        yield SearchService(DocumentRepository(db))
    finally:
        client.close()
