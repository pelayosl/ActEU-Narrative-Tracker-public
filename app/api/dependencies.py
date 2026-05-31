from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.exceptions import InvalidToken, TokenExpired, UserNotFound
from app.infrastructure.job_queue_service import JobQueueService
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.mongodb import db
from app.infrastructure.password_hasher import PasswordHasher
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.topic_repository import TopicRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import User
from app.services.auth_service import AuthService
from app.services.classification_service import ClassificationService
from app.services.project_service import ProjectService
from app.services.search_service import SearchService
from app.services.topic_modelling_service import TopicModellingService
from app.services.visualisation_service import VisualisationService
from app.tasks.celery_app import celery_app
from app.config import settings

security = HTTPBearer()


def get_db() -> AsyncIOMotorDatabase:
    return db


def get_user_repo(db_instance: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> UserRepository:
    return UserRepository(db_instance)


def get_document_repo(db_instance: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> DocumentRepository:
    return DocumentRepository(db_instance)


def get_project_repo(db_instance: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> ProjectRepository:
    return ProjectRepository(db_instance)


def get_topic_repo(db_instance: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> TopicRepository:
    return TopicRepository(db_instance)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    hasher: Annotated[PasswordHasher, Depends()],
    jwt_handler: Annotated[JWTHandler, Depends()],
) -> AuthService:
    return AuthService(user_repo, hasher, jwt_handler)


def get_search_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
) -> SearchService:
    return SearchService(document_repo)


def get_project_service(
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    topic_repo: Annotated[TopicRepository, Depends(get_topic_repo)],
) -> ProjectService:
    return ProjectService(project_repo, topic_repo)


def get_visualisation_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> VisualisationService:
    return VisualisationService(document_repo, project_service)


def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def get_job_queue(redis: Annotated[Redis, Depends(get_redis)]) -> JobQueueService:
    return JobQueueService(celery_app, redis)


def get_classification_service(
    job_queue: Annotated[JobQueueService, Depends(get_job_queue)],
) -> ClassificationService:
    return ClassificationService(job_queue)


def get_topic_modelling_service(
    job_queue: Annotated[JobQueueService, Depends(get_job_queue)],
) -> TopicModellingService:
    return TopicModellingService(job_queue)


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