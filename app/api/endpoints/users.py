from fastapi import APIRouter

from app.api.dependencies import CurrentUser, Database
from app.schemas.auth import UserResponse
from app.services.user_service import list_users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_all_users(_: CurrentUser, db: Database) -> list[UserResponse]:
    return await list_users(db)
