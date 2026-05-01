from fastapi import APIRouter, Depends, HTTPException, status

from app.exceptions import InvalidCredentials, InvalidToken, TokenExpired, UsernameTaken
from app.schemas.auth import AuthToken, RegistrationForm, User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=AuthToken)
async def login(
    username: str,
    password: str,
    service: AuthService = Depends(),
) -> AuthToken:
    try:
        return await service.login(username, password)
    except InvalidCredentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    form: RegistrationForm,
    service: AuthService = Depends(),
) -> User:
    try:
        return await service.register_user(form)
    except UsernameTaken as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
