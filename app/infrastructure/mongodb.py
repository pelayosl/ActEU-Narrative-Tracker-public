"""Process-wide MongoDB client and database handle.

Creates the single shared async Motor/PyMongo client used by the FastAPI process and
exposes the configured database as ``db``, which the API dependency layer injects into
repositories. Celery tasks open their own short-lived clients instead (see
``app.tasks.task_context``).
"""

from pymongo import AsyncMongoClient
from app.config import settings

# DB down fails fast --> 5 seconds
client = AsyncMongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB]
