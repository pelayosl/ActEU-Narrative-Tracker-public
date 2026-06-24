
from pymongo import AsyncMongoClient
from app.config import settings

# DB down fails fast --> 5 seconds
client = AsyncMongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
db = client[settings.MONGODB_DB]
