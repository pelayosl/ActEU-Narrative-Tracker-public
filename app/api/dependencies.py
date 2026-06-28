"""FastAPI dependency providers wiring repositories, services and infrastructure.

Each ``get_*`` function is a ``Depends()`` factory that the route handlers use for
injection, so the API layer never constructs repositories directly. The two auth
dependencies translate domain auth exceptions into HTTP responses.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.asynchronous.database import AsyncDatabase
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


def get_db() -> AsyncDatabase:
    """Provide the shared MongoDB database handle.

    :returns: The process-wide :class:`AsyncDatabase`.
    """
    return db


def get_user_repo(db_instance: Annotated[AsyncDatabase, Depends(get_db)]) -> UserRepository:
    """Provide a :class:`UserRepository` bound to the request database.

    :param db_instance: The injected database handle.
    :returns: A user repository.
    """
    return UserRepository(db_instance)


def get_document_repo(db_instance: Annotated[AsyncDatabase, Depends(get_db)]) -> DocumentRepository:
    """Provide a :class:`DocumentRepository` bound to the request database.

    :param db_instance: The injected database handle.
    :returns: A document repository.
    """
    return DocumentRepository(db_instance)


def get_project_repo(db_instance: Annotated[AsyncDatabase, Depends(get_db)]) -> ProjectRepository:
    """Provide a :class:`ProjectRepository` bound to the request database.

    :param db_instance: The injected database handle.
    :returns: A project repository.
    """
    return ProjectRepository(db_instance)


def get_topic_repo(db_instance: Annotated[AsyncDatabase, Depends(get_db)]) -> TopicRepository:
    """Provide a :class:`TopicRepository` bound to the request database.

    :param db_instance: The injected database handle.
    :returns: A topic repository.
    """
    return TopicRepository(db_instance)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    hasher: Annotated[PasswordHasher, Depends()],
    jwt_handler: Annotated[JWTHandler, Depends()],
) -> AuthService:
    """Assemble an :class:`AuthService` from its repository and infrastructure adapters.

    :param user_repo: The user repository.
    :param hasher: The password hasher.
    :param jwt_handler: The JWT handler.
    :returns: A configured auth service.
    """
    return AuthService(user_repo, hasher, jwt_handler)


def get_search_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
) -> SearchService:
    """Assemble a :class:`SearchService` from the document repository.

    :param document_repo: The document repository.
    :returns: A configured search service.
    """
    return SearchService(document_repo)


def get_project_service(
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    topic_repo: Annotated[TopicRepository, Depends(get_topic_repo)],
) -> ProjectService:
    """Assemble a :class:`ProjectService` from the project and topic repositories.

    :param project_repo: The project repository.
    :param topic_repo: The topic repository.
    :returns: A configured project service.
    """
    return ProjectService(project_repo, topic_repo)


def get_visualisation_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> VisualisationService:
    """Assemble a :class:`VisualisationService` from the document repo and project service.

    :param document_repo: The document repository.
    :param project_service: The project service, used to resolve project subtopics.
    :returns: A configured visualisation service.
    """
    return VisualisationService(document_repo, project_service)


def get_redis() -> Redis:
    """Provide an async Redis client built from settings.

    :returns: A new :class:`Redis` client.
    """
    return Redis.from_url(settings.REDIS_URL)


def get_job_queue(redis: Annotated[Redis, Depends(get_redis)]) -> JobQueueService:
    """Assemble a :class:`JobQueueService` from the Celery app and Redis client.

    :param redis: The Redis client.
    :returns: A configured job queue service.
    """
    return JobQueueService(celery_app, redis)


def get_classification_service(
    job_queue: Annotated[JobQueueService, Depends(get_job_queue)],
) -> ClassificationService:
    """Assemble a :class:`ClassificationService` from the job queue.

    :param job_queue: The job queue service.
    :returns: A configured classification service.
    """
    return ClassificationService(job_queue)


def get_topic_modelling_service(
    job_queue: Annotated[JobQueueService, Depends(get_job_queue)],
) -> TopicModellingService:
    """Assemble a :class:`TopicModellingService` from the job queue.

    :param job_queue: The job queue service.
    :returns: A configured topic modelling service.
    """
    return TopicModellingService(job_queue)


async def get_current_user(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Resolve the authenticated user from the bearer token, used on protected routes.

    :param auth_service: The auth service used to verify the token.
    :param credentials: The bearer credentials extracted from the request.
    :returns: The authenticated :class:`User`.
    :raises HTTPException: 401 if the token is expired, invalid, or names no user.
    """
    try:
        return await auth_service.verify_token(credentials.credentials)
    except TokenExpired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (InvalidToken, UserNotFound):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require that the authenticated user has the admin role.

    :param current_user: The authenticated user.
    :returns: The same user when they are an admin.
    :raises HTTPException: 403 if the user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user