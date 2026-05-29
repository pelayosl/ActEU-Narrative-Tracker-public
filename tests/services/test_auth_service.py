from unittest.mock import AsyncMock, MagicMock
import pytest

from app.exceptions import InvalidCredentials, InvalidToken, TokenExpired, UsernameTaken, UserNotFound
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.password_hasher import PasswordHasher
from app.schemas.auth import RegistrationForm, User
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(**overrides) -> User:
    base = dict(
        user_id="user-123",
        name="Ada",
        surname="Lovelace",
        username="ada",
        hashed_password=PasswordHasher().hash("secret"),
        role="user",
    )
    base.update(overrides)
    return User(**base)


def make_form(**overrides) -> RegistrationForm:
    base = dict(name="Ada", surname="Lovelace", username="ada", password="secret", role="user")
    base.update(overrides)
    return RegistrationForm(**base)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def jwt() -> JWTHandler:
    return JWTHandler()


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(user_repo, hasher, jwt) -> AuthService:
    return AuthService(user_repo, hasher, jwt)


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------

class TestLogin:
    async def test_valid_credentials_returns_token(self, service, user_repo):
        user_repo.find_by_username.return_value = make_user()
        token = await service.login("ada", "secret")
        user_repo.find_by_username.assert_awaited_once_with("ada")
        assert token.access_token
        assert token.token_type == "bearer"

    async def test_wrong_password_raises(self, service, user_repo):
        user_repo.find_by_username.return_value = make_user()
        with pytest.raises(InvalidCredentials):
            await service.login("ada", "wrongpassword")

    async def test_unknown_user_raises(self, service, user_repo):
        user_repo.find_by_username.return_value = None
        with pytest.raises(InvalidCredentials):
            await service.login("nobody", "secret")

    async def test_token_contains_expected_claims(self, service, user_repo, jwt):
        user_repo.find_by_username.return_value = make_user()
        token = await service.login("ada", "secret")
        payload = jwt.decode(token.access_token)
        assert payload["username"] == "ada"
        assert payload["role"] == "user"
        assert payload["sub"] == "user-123"


# ---------------------------------------------------------------------------
# verify_token()
# ---------------------------------------------------------------------------

class TestVerifyToken:
    async def test_valid_token_returns_user(self, service, user_repo, jwt):
        user = make_user()
        user_repo.find_by_username.return_value = user
        token = jwt.encode({"sub": user.user_id, "username": user.username, "role": user.role})
        result = await service.verify_token(token)
        user_repo.find_by_username.assert_awaited_once_with("ada")
        assert result.username == "ada"

    async def test_expired_token_raises(self, service):
        # A token signed with the right key but already expired
        from datetime import datetime, timezone, timedelta
        import jwt as pyjwt
        from app.config import settings
        expired_token = pyjwt.encode(
            {"sub": "x", "username": "ada", "role": "user", "exp": datetime(2000, 1, 1, tzinfo=timezone.utc)},
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(TokenExpired):
            await service.verify_token(expired_token)

    async def test_invalid_token_raises(self, service):
        with pytest.raises(InvalidToken):
            await service.verify_token("not.a.valid.token")

    async def test_token_with_wrong_signature_raises(self, service):
        from datetime import datetime, timedelta, timezone
        import jwt as pyjwt
        payload = {
            "sub": "user-123",
            "username": "ada",
            "role": "user",
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=5),
        }
        token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(InvalidToken):
            await service.verify_token(token)

    async def test_token_for_deleted_user_raises(self, service, user_repo, jwt):
        token = jwt.encode({"sub": "x", "username": "ghost", "role": "user"})
        user_repo.find_by_username.return_value = None
        with pytest.raises(UserNotFound):
            await service.verify_token(token)

    async def test_token_username_controls_lookup(self, service, user_repo, jwt):
        user = make_user(user_id="user-999")
        user_repo.find_by_username.return_value = user
        token = jwt.encode({"sub": "user-123", "username": "ada", "role": "user"})
        result = await service.verify_token(token)
        assert result.user_id == "user-999"


# ---------------------------------------------------------------------------
# register_user()
# ---------------------------------------------------------------------------

class TestRegisterUser:
    async def test_new_user_is_saved_and_returned(self, service, user_repo):
        user_repo.find_by_username.return_value = None
        user = await service.register_user(make_form())
        user_repo.save.assert_awaited_once()
        assert user.username == "ada"
        assert user.role == "user"

    async def test_password_is_hashed(self, service, user_repo, hasher):
        user_repo.find_by_username.return_value = None
        user = await service.register_user(make_form())
        assert user.hashed_password != "secret"
        assert hasher.verify("secret", user.hashed_password)

    async def test_duplicate_username_raises(self, service, user_repo):
        user_repo.find_by_username.return_value = make_user()
        with pytest.raises(UsernameTaken):
            await service.register_user(make_form())
        user_repo.find_by_username.assert_awaited_once_with("ada")

    async def test_returned_user_has_generated_id(self, service, user_repo):
        user_repo.find_by_username.return_value = None
        user = await service.register_user(make_form())
        assert user.user_id  # non-empty
