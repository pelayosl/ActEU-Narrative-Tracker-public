from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


class JWTHandler:
    """Adapter over PyJWT."""

    def encode(self, payload: dict) -> str:
        data = payload.copy()
        data["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
        return jwt.encode(data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def decode(self, token: str) -> dict:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
