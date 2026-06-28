from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.exceptions import InvalidToken, TokenExpired


class JWTHandler:
    """Adapter over PyJWT that translates library errors into domain exceptions."""

    def encode(self, payload: dict) -> str:
        """Sign a payload into a JWT, adding an expiry claim.

        :param payload: The claims to embed (an ``exp`` claim is added automatically).
        :returns: The signed JWT string.
        """
        data = payload.copy()
        data["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
        return jwt.encode(data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def decode(self, token: str) -> dict:
        """Verify and decode a JWT into its claims.

        PyJWT errors are caught and re-raised as domain exceptions, so the service
        layer never sees PyJWT types.

        :param token: The JWT string to decode.
        :returns: The decoded claims dict.
        :raises TokenExpired: If the token's signature has expired.
        :raises InvalidToken: If the token is otherwise malformed or invalid.
        """
        try:
            return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise TokenExpired()
        except jwt.InvalidTokenError:
            raise InvalidToken()
