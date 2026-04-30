from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.password_hasher import PasswordHasher
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthToken, RegistrationForm, User


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        hasher: PasswordHasher,
        jwt: JWTHandler,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher
        self._jwt = jwt

    async def login(self, username: str, password: str) -> AuthToken:
        raise NotImplementedError

    async def verify_token(self, token: str) -> User:
        raise NotImplementedError

    async def register_user(self, form: RegistrationForm) -> User:
        raise NotImplementedError
