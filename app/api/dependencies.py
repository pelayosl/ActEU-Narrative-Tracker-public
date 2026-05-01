from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.exceptions import InvalidToken, TokenExpired, UserNotFound
from app.schemas.auth import User
from app.services.auth_service import AuthService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(),
) -> User:
    """Auth middleware — applied to all protected routes via Depends()."""
    try:
        return await auth_service.verify_token(credentials.credentials)
    except TokenExpired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except (InvalidToken, UserNotFound):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
