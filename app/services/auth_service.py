import uuid

from app.exceptions import InvalidCredentials, TokenExpired, InvalidToken, UserNotFound, UsernameTaken
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.password_hasher import PasswordHasher
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthToken, RegistrationForm, User


class AuthService:
    """Authentication and user-registration logic.

    Coordinates the user repository with the password and JWT infrastructure adapters
    to authenticate credentials, issue and verify tokens, and register new accounts.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        hasher: PasswordHasher,
        jwt_handler: JWTHandler,
    ) -> None:
        """Store the repository and infrastructure adapters this service depends on.

        :param user_repo: Repository for user persistence and lookup.
        :param hasher: Adapter for password hashing and verification.
        :param jwt_handler: Adapter for encoding and decoding JWTs.
        """
        self._user_repo = user_repo
        self._hasher = hasher
        self._jwt = jwt_handler

    async def login(self, username: str, password: str) -> AuthToken:
        """Authenticate a user and issue a signed access token.

        :param username: The username to authenticate.
        :param password: The plaintext password to verify.
        :returns: An :class:`AuthToken` carrying the signed JWT.
        :raises InvalidCredentials: If the user does not exist or the password is wrong.
        """
        user = await self._user_repo.find_by_username(username)
        if not user or not self._hasher.verify(password, user.hashed_password):
            raise InvalidCredentials()
        token = self._jwt.encode({"sub": user.user_id, "username": user.username, "role": user.role})
        return AuthToken(access_token=token)

    async def verify_token(self, token: str) -> User:
        """Validate an access token and return the user it identifies.

        :param token: The JWT to validate.
        :returns: The :class:`User` named in the token.
        :raises TokenExpired: If the token has expired.
        :raises InvalidToken: If the token is malformed or its signature is invalid.
        :raises UserNotFound: If the token is valid but names no existing user.
        """
        payload = self._jwt.decode(token)  # raises TokenExpired or InvalidToken
        user = await self._user_repo.find_by_username(payload["username"])
        if not user:
            raise UserNotFound()
        return user

    async def register_user(self, form: RegistrationForm) -> User:
        """Create a new user account with a hashed password.

        :param form: The registration details (name, surname, username, password, role).
        :returns: The newly created :class:`User`.
        :raises UsernameTaken: If the username already exists.
        """
        if await self._user_repo.find_by_username(form.username):
            raise UsernameTaken(form.username)
        user = User(
            user_id=str(uuid.uuid4()),
            name=form.name,
            surname=form.surname,
            username=form.username,
            hashed_password=self._hasher.hash(form.password),
            role=form.role,
        )
        await self._user_repo.save(user)
        return user
