import uuid

from app.exceptions import InvalidCredentials, TokenExpired, InvalidToken, UserNotFound, UsernameTaken
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.password_hasher import PasswordHasher
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthToken, RegistrationForm, User


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        hasher: PasswordHasher,
        jwt_handler: JWTHandler,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher
        self._jwt = jwt_handler

    async def login(self, username: str, password: str) -> AuthToken:
        user = await self._user_repo.find_by_username(username)
        if not user or not self._hasher.verify(password, user.hashed_pswd):
            raise InvalidCredentials()
        token = self._jwt.encode({"sub": user.user_id, "username": user.username, "role": user.role})
        return AuthToken(access_token=token)

    async def verify_token(self, token: str) -> User:
        payload = self._jwt.decode(token)  # raises TokenExpired or InvalidToken
        user = await self._user_repo.find_by_username(payload["username"])
        if not user:
            raise UserNotFound()
        return user

    async def register_user(self, form: RegistrationForm) -> User:
        if await self._user_repo.find_by_username(form.username):
            raise UsernameTaken(form.username)
        user = User(
            user_id=str(uuid.uuid4()),
            name=form.name,
            surname=form.surname,
            username=form.username,
            hashed_pswd=self._hasher.hash(form.password),
            role=form.role,
        )
        await self._user_repo.save(user)
        return user
