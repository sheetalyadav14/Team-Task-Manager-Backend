from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.security import decode_access_token
from app.database.mongo import get_database
from app.schemas.auth import UserResponse
from app.services.user_service import get_user_by_id

_security = HTTPBearer(auto_error=False)


def get_db() -> AsyncIOMotorDatabase[Any]:
    return get_database()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)],
    db: Annotated[AsyncIOMotorDatabase[Any], Depends(get_db)],
) -> UserResponse:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def require_admin(user: Annotated[UserResponse, Depends(get_current_user)]) -> UserResponse:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
AdminUser = Annotated[UserResponse, Depends(require_admin)]
Database = Annotated[AsyncIOMotorDatabase[Any], Depends(get_db)]
