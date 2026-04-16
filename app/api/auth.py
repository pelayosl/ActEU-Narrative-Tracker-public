from fastapi import APIRouter, Depends

from app.schemas.auth import AuthToken, RegistrationForm, User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthToken)
async def login(
    username: str,
    password: str,
    service: AuthService = Depends(),
) -> AuthToken:
    raise NotImplementedError


@router.post("/register", response_model=User)
async def register(
    form: RegistrationForm,
    service: AuthService = Depends(),
) -> User:
    raise NotImplementedError
