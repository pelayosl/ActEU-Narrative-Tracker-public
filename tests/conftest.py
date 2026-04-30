import pytest
from motor.motor_asyncio import AsyncIOMotorClient

TEST_MONGO_URI = "mongodb://localhost:27017"
TEST_DB_NAME = "acteu_test"


@pytest.fixture
async def db():
    client = AsyncIOMotorClient(TEST_MONGO_URI)
    database = client[TEST_DB_NAME]
    yield database
    # Drop all collections after each test to ensure isolation
    for name in await database.list_collection_names():
        await database.drop_collection(name)
    client.close()
