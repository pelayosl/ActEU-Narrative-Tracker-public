import importlib.util
import sys
import types

import pytest
from pymongo import AsyncMongoClient

# FastText (requirements-nlp.txt) is absent from the CI/dev environment, but some
# task modules import ClassifierWrapper -> `import fasttext` at module load. Insert
# a stub so those modules import cleanly for the non-slow tests that fully mock the
# wrapper. Done in conftest (loaded before any test module) so the behaviour is
# deterministic regardless of collection order. The `_is_stub` flag lets the slow
# FastText tests skip themselves when real FastText is not installed.
if importlib.util.find_spec("fasttext") is None:
    _fasttext_stub = types.ModuleType("fasttext")
    _fasttext_stub._is_stub = True
    sys.modules["fasttext"] = _fasttext_stub


def fasttext_unavailable() -> bool:
    """True when the real FastText library is not installed (only the stub is present)."""
    import fasttext
    return getattr(fasttext, "_is_stub", False)


TEST_MONGO_URI = "mongodb://localhost:27017"
TEST_DB_NAME = "acteu_test"


@pytest.fixture
async def db():
    client = AsyncMongoClient(TEST_MONGO_URI)
    database = client[TEST_DB_NAME]
    yield database
    # Drop all collections after each test to ensure isolation
    for name in await database.list_collection_names():
        await database.drop_collection(name)
    await client.close()
