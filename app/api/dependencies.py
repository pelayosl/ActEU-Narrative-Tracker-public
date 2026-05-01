from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.exceptions import InvalidToken, TokenExpired, UserNotFound
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.mongodb import db
from app.infrastructure.password_hasher import PasswordHasher
from app.repositories.user_repository import UserRepository
from app.schemas.auth import User
from app.services.auth_service import AuthService

security = HTTPBearer()


def get_db() -> AsyncIOMotorDatabase:
    return db


def get_user_repo(db_instance: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> UserRepository:
    return UserRepository(db_instance)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    hasher: Annotated[PasswordHasher, Depends()],
    jwt_handler: Annotated[JWTHandler, Depends()],
) -> AuthService:
    return AuthService(user_repo, hasher, jwt_handler)


async def get_current_user(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Auth middleware — applied to all protected routes via Depends()."""
    try:
        return await auth_service.verify_token(credentials.credentials)
    except TokenExpired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (InvalidToken, UserNotFound):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user