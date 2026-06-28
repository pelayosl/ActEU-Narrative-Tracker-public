from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service, get_current_admin
from app.exceptions import InvalidCredentials, UsernameTaken
from app.schemas.auth import AuthToken, LoginForm, RegistrationForm, User, UserPublic
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    form: LoginForm,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthToken:
    """Authenticate credentials and return a bearer token.

    :param form: The login credentials.
    :param service: The injected auth service.
    :returns: An :class:`AuthToken` on success.
    :raises HTTPException: 401 if the credentials are invalid.
    """
    try:
        return await service.login(form.username, form.password)
    except InvalidCredentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    form: RegistrationForm,
    service: Annotated[AuthService, Depends(get_auth_service)],
    _: Annotated[User, Depends(get_current_admin)],
) -> User:
    """Register a new user account (admin only).

    :param form: The new user's registration details.
    :param service: The injected auth service.
    :param _: The authenticated admin, enforced by the dependency.
    :returns: The created user, serialised as :class:`UserPublic`.
    :raises HTTPException: 409 if the username is already taken.
    """
    try:
        return await service.register_user(form)
    except UsernameTaken as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
