
from pymongo import AsyncMongoClient
from app.config import settings

client = AsyncMongoClient(settings.MONGODB_URL)
db = client[settings.MONGODB_DB]
