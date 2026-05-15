from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config.settings import get_settings


class _Database:
    client: AsyncIOMotorClient[Any] | None = None
    db: AsyncIOMotorDatabase[Any] | None = None


_state = _Database()


async def connect_to_mongo() -> None:
    settings = get_settings()
    _state.client = AsyncIOMotorClient(settings.mongodb_uri)
    _state.db = _state.client[settings.mongodb_db_name]
    await ensure_indexes(_state.db)


async def close_mongo_connection() -> None:
    if _state.client is not None:
        _state.client.close()
        _state.client = None
        _state.db = None


def get_database() -> AsyncIOMotorDatabase[Any]:
    if _state.db is None:
        raise RuntimeError("Database has not been initialised; call connect_to_mongo() first")
    return _state.db


def set_test_database(db: AsyncIOMotorDatabase[Any]) -> None:
    _state.db = db


async def ensure_indexes(db: AsyncIOMotorDatabase[Any]) -> None:
    await db["users"].create_index("email", unique=True)
    await db["projects"].create_index("owner_id")
    await db["projects"].create_index("members.user_id")
    await db["tasks"].create_index("project_id")
    await db["tasks"].create_index("assignee_id")
    await db["tasks"].create_index("status")
