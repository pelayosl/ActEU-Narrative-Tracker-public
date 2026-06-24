"""Integration tests for the /auth router and the cross-cutting auth middleware.

These exercise the *real* AuthService / JWTHandler / PasswordHasher stack against the
test DB — `get_current_user` is NOT overridden here (we want the real token path).
"""

import pytest

from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.password_hasher import PasswordHasher

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def insert_user(db, *, username, password, role="user", user_id="u-1"):
    """Insert a user with a real bcrypt hash so login() can verify it."""
    hashed = PasswordHasher().hash(password)
    await db["users"].insert_one(
        {
            "user_id": user_id,
            "name": "Test",
            "surname": "User",
            "username": username,
            "hashed_password": hashed,
            "role": role,
        }
    )


def bearer_for(user_id, username, role) -> dict:
    token = JWTHandler().encode({"sub": user_id, "username": username, "role": role})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    async def test_valid_credentials_return_token(self, client, db):
        await insert_user(db, username="alice", password="s3cret")

        res = await client.post("/auth/login", json={"username": "alice", "password": "s3cret"})

        assert res.status_code == 200
        body = res.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    async def test_wrong_password_returns_401(self, client, db):
        await insert_user(db, username="alice", password="s3cret")

        res = await client.post("/auth/login", json={"username": "alice", "password": "nope"})

        assert res.status_code == 401

    async def test_unknown_user_returns_401(self, client, db):
        res = await client.post("/auth/login", json={"username": "ghost", "password": "x"})

        assert res.status_code == 401

    async def test_malformed_body_returns_422(self, client):
        res = await client.post("/auth/login", json={"username": "alice"})

        assert res.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/register (admin-only)
# ---------------------------------------------------------------------------

REG_FORM = {
    "name": "New",
    "surname": "Person",
    "username": "newbie",
    "password": "pw12345",
    "role": "user",
}


class TestRegister:
    async def test_admin_can_register_and_response_hides_password(self, client, db):
        await insert_user(db, username="boss", password="pw", role="admin", user_id="admin-1")
        headers = bearer_for("admin-1", "boss", "admin")

        res = await client.post("/auth/register", json=REG_FORM, headers=headers)

        assert res.status_code == 201
        body = res.json()
        assert body["username"] == "newbie"
        assert body["role"] == "user"
        assert "hashed_password" not in body  # UserPublic never leaks the hash
        # user really persisted
        assert await db["users"].find_one({"username": "newbie"}) is not None

    async def test_non_admin_is_forbidden(self, client, db):
        await insert_user(db, username="plain", password="pw", role="user", user_id="u-2")
        headers = bearer_for("u-2", "plain", "user")

        res = await client.post("/auth/register", json=REG_FORM, headers=headers)

        assert res.status_code == 403

    async def test_duplicate_username_returns_409(self, client, db):
        await insert_user(db, username="boss", password="pw", role="admin", user_id="admin-1")
        await insert_user(db, username="newbie", password="pw", user_id="dup-1")
        headers = bearer_for("admin-1", "boss", "admin")

        res = await client.post("/auth/register", json=REG_FORM, headers=headers)

        assert res.status_code == 409


# ---------------------------------------------------------------------------
# Cross-cutting auth middleware
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    async def test_missing_token_is_rejected(self, client):
        # HTTPBearer with no Authorization header -> not authenticated (401/403)
        res = await client.get("/projects")
        assert res.status_code in (401, 403)

    async def test_invalid_token_returns_401(self, client):
        res = await client.get("/projects", headers={"Authorization": "Bearer not-a-jwt"})
        assert res.status_code == 401

    async def test_valid_token_for_unknown_user_returns_401(self, client):
        # Well-formed JWT but the user is not in the DB -> UserNotFound -> 401
        headers = bearer_for("ghost-id", "ghost", "user")
        res = await client.get("/projects", headers=headers)
        assert res.status_code == 401
