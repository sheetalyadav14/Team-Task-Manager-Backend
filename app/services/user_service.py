from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config.security import hash_password, verify_password
from app.models.types import UserRole
from app.schemas.auth import UserResponse


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def _user_to_response(document: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        role=document["role"],
    )


async def create_user(
    db: AsyncIOMotorDatabase[Any],
    *,
    name: str,
    email: str,
    password: str,
    role: UserRole = "member",
) -> UserResponse:
    normalized_email = email.lower().strip()
    existing = await db["users"].find_one({"email": normalized_email})
    if existing is not None:
        raise EmailAlreadyExistsError("Email is already registered")
    now = datetime.now(timezone.utc)
    document = {
        "name": name.strip(),
        "email": normalized_email,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["users"].insert_one(document)
    document["_id"] = result.inserted_id
    return _user_to_response(document)


async def authenticate_user(
    db: AsyncIOMotorDatabase[Any],
    *,
    email: str,
    password: str,
) -> UserResponse:
    document = await db["users"].find_one({"email": email.lower().strip()})
    if document is None or not verify_password(password, document["password_hash"]):
        raise InvalidCredentialsError("Invalid email or password")
    return _user_to_response(document)


async def get_user_by_id(db: AsyncIOMotorDatabase[Any], user_id: str) -> UserResponse | None:
    if not ObjectId.is_valid(user_id):
        return None
    document = await db["users"].find_one({"_id": ObjectId(user_id)})
    if document is None:
        return None
    return _user_to_response(document)


async def list_users(db: AsyncIOMotorDatabase[Any]) -> list[UserResponse]:
    cursor = db["users"].find({}, projection={"password_hash": 0}).sort("name", 1)
    return [_user_to_response(doc) async for doc in cursor]
