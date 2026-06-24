"""Shared fixtures for the FastAPI integration tests.

These tests drive the real ASGI app in-process through httpx + ASGITransport (no live
uvicorn, no sockets). Policy (see z_context/testing_strategy.md §2):

* the real service -> repository stack runs against the `acteu_test` Mongo DB for
  synchronous routes (`get_db` is overridden to the per-test database);
* `get_current_user` is overridden with a seeded user for most tests, so we don't mint a
  token in every test — a handful of auth tests exercise the real JWT path instead;
* task-dispatching services and the job queue are faked so Celery / BERTopic / FastText
  never run in CI.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import dependencies as deps
from app.main import app
from app.schemas.auth import User


# ---------------------------------------------------------------------------
# User helpers / seeding
# ---------------------------------------------------------------------------

def make_user(**overrides) -> User:
    base = {
        "user_id": "user-int-1",
        "name": "Ana",
        "surname": "Lopez",
        "username": "alopez",
        "hashed_password": "hashed-secret",
        "role": "user",
    }
    base.update(overrides)
    return User(**base)


@pytest.fixture
def current_user() -> User:
    """The user that `get_current_user` is overridden to return in most tests."""
    return make_user()


@pytest.fixture
async def seed_user(db, current_user):
    """Insert `current_user` into the test DB so real service calls (e.g. login,
    ownership checks) resolve it. Returns the inserted User."""
    await db["users"].insert_one(current_user.model_dump())
    return current_user


# ---------------------------------------------------------------------------
# Fake task-dispatching services (Celery must not run in CI)
# ---------------------------------------------------------------------------

FAKE_JOB_ID = "job-fake-123"
BASE_URL="http://test"


class FakeClassificationService:
    def submit_training(self, topics, project_id, name) -> str:
        return FAKE_JOB_ID

    def submit_labelling(self, project_id, classifier_id, query) -> str:
        return FAKE_JOB_ID


class FakeTopicModellingService:
    def submit_generation(self, project_id, doc_ids) -> str:
        return FAKE_JOB_ID

    def submit_reconciliation(self, project_id, topics, passthrough_topics=None) -> str:
        return FAKE_JOB_ID


# ---------------------------------------------------------------------------
# App + dependency-override plumbing
# ---------------------------------------------------------------------------

@pytest.fixture
def override(db):
    """Helper that installs dependency overrides and tears them down after the test.

    `get_db` is always pointed at the per-test `acteu_test` database, and the two
    task-dispatching services are always faked. Tests add `get_current_user` etc. on top.
    """
    app.dependency_overrides[deps.get_db] = lambda: db
    app.dependency_overrides[deps.get_classification_service] = FakeClassificationService
    app.dependency_overrides[deps.get_topic_modelling_service] = FakeTopicModellingService

    def _set(dependency, value):
        app.dependency_overrides[dependency] = value

    yield _set
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override):
    """Unauthenticated client (real `get_current_user` — protected routes will 401)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as c:
        yield c


@pytest.fixture
async def auth_client(override, current_user):
    """Client with `get_current_user` overridden to a seeded regular user."""
    override(deps.get_current_user, lambda: current_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as c:
        yield c


@pytest.fixture
async def admin_client(override):
    """Client authenticated as an admin (covers admin-only routes)."""
    admin = make_user(user_id="admin-int-1", username="admin", role="admin")
    override(deps.get_current_user, lambda: admin)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as c:
        yield c
