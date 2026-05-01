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
    try:
        return await service.register_user(form)
    except UsernameTaken as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
