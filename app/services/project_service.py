from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.types import ProjectMemberRole, to_object_id
from app.schemas.project import ProjectMemberResponse, ProjectResponse


class ProjectNotFoundError(Exception):
    pass


class NotProjectMemberError(Exception):
    pass


class NotProjectAdminError(Exception):
    pass


def _project_to_response(document: dict[str, Any], member_users: dict[str, dict[str, Any]] | None = None) -> ProjectResponse:
    members: list[ProjectMemberResponse] = []
    for member in document.get("members", []):
        user_id = str(member["user_id"])
        user_info = (member_users or {}).get(user_id)
        members.append(
            ProjectMemberResponse(
                user_id=user_id,
                role=member["role"],
                name=user_info["name"] if user_info else None,
                email=user_info["email"] if user_info else None,
            )
        )
    return ProjectResponse(
        id=str(document["_id"]),
        name=document["name"],
        description=document.get("description", ""),
        owner_id=str(document["owner_id"]),
        members=members,
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


async def _hydrate_members(db: AsyncIOMotorDatabase[Any], project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    member_ids = [m["user_id"] for m in project.get("members", [])]
    if not member_ids:
        return {}
    cursor = db["users"].find({"_id": {"$in": member_ids}}, projection={"name": 1, "email": 1})
    return {str(doc["_id"]): doc async for doc in cursor}


async def create_project(
    db: AsyncIOMotorDatabase[Any],
    *,
    owner_id: str,
    name: str,
    description: str,
) -> ProjectResponse:
    owner_object_id = to_object_id(owner_id)
    now = datetime.now(timezone.utc)
    document = {
        "name": name.strip(),
        "description": description.strip(),
        "owner_id": owner_object_id,
        "members": [{"user_id": owner_object_id, "role": "admin"}],
        "created_at": now,
        "updated_at": now,
    }
    result = await db["projects"].insert_one(document)
    document["_id"] = result.inserted_id
    hydrated = await _hydrate_members(db, document)
    return _project_to_response(document, hydrated)


async def list_projects_for_user(db: AsyncIOMotorDatabase[Any], user_id: str) -> list[ProjectResponse]:
    user_object_id = to_object_id(user_id)
    cursor = db["projects"].find({"members.user_id": user_object_id}).sort("created_at", -1)
    projects: list[ProjectResponse] = []
    async for document in cursor:
        hydrated = await _hydrate_members(db, document)
        projects.append(_project_to_response(document, hydrated))
    return projects


async def get_project(db: AsyncIOMotorDatabase[Any], project_id: str, user_id: str) -> ProjectResponse:
    document = await _require_member(db, project_id, user_id)
    hydrated = await _hydrate_members(db, document)
    return _project_to_response(document, hydrated)


async def update_project(
    db: AsyncIOMotorDatabase[Any],
    *,
    project_id: str,
    user_id: str,
    name: str | None,
    description: str | None,
) -> ProjectResponse:
    document = await _require_admin(db, project_id, user_id)
    update: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    if name is not None:
        update["name"] = name.strip()
    if description is not None:
        update["description"] = description.strip()
    await db["projects"].update_one({"_id": document["_id"]}, {"$set": update})
    refreshed = await db["projects"].find_one({"_id": document["_id"]})
    if refreshed is None:
        raise ProjectNotFoundError("Project not found")
    hydrated = await _hydrate_members(db, refreshed)
    return _project_to_response(refreshed, hydrated)


async def delete_project(db: AsyncIOMotorDatabase[Any], *, project_id: str, user_id: str) -> None:
    document = await _require_admin(db, project_id, user_id)
    await db["tasks"].delete_many({"project_id": document["_id"]})
    await db["projects"].delete_one({"_id": document["_id"]})


async def add_member(
    db: AsyncIOMotorDatabase[Any],
    *,
    project_id: str,
    requester_id: str,
    new_member_id: str,
    role: ProjectMemberRole,
) -> ProjectResponse:
    document = await _require_admin(db, project_id, requester_id)
    new_member_object_id = to_object_id(new_member_id)
    user_exists = await db["users"].find_one({"_id": new_member_object_id})
    if user_exists is None:
        raise ProjectNotFoundError("User does not exist")
    already_member = any(m["user_id"] == new_member_object_id for m in document.get("members", []))
    if not already_member:
        await db["projects"].update_one(
            {"_id": document["_id"]},
            {
                "$push": {"members": {"user_id": new_member_object_id, "role": role}},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
    refreshed = await db["projects"].find_one({"_id": document["_id"]})
    if refreshed is None:
        raise ProjectNotFoundError("Project not found")
    hydrated = await _hydrate_members(db, refreshed)
    return _project_to_response(refreshed, hydrated)


async def remove_member(
    db: AsyncIOMotorDatabase[Any],
    *,
    project_id: str,
    requester_id: str,
    member_id: str,
) -> ProjectResponse:
    document = await _require_admin(db, project_id, requester_id)
    member_object_id = to_object_id(member_id)
    if member_object_id == document["owner_id"]:
        raise NotProjectAdminError("Cannot remove the project owner")
    await db["projects"].update_one(
        {"_id": document["_id"]},
        {
            "$pull": {"members": {"user_id": member_object_id}},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    refreshed = await db["projects"].find_one({"_id": document["_id"]})
    if refreshed is None:
        raise ProjectNotFoundError("Project not found")
    hydrated = await _hydrate_members(db, refreshed)
    return _project_to_response(refreshed, hydrated)


async def _require_member(
    db: AsyncIOMotorDatabase[Any], project_id: str, user_id: str
) -> dict[str, Any]:
    document = await db["projects"].find_one({"_id": to_object_id(project_id)})
    if document is None:
        raise ProjectNotFoundError("Project not found")
    user_object_id = to_object_id(user_id)
    is_member = any(m["user_id"] == user_object_id for m in document.get("members", []))
    if not is_member:
        raise NotProjectMemberError("Not a member of this project")
    return document


async def _require_admin(
    db: AsyncIOMotorDatabase[Any], project_id: str, user_id: str
) -> dict[str, Any]:
    document = await _require_member(db, project_id, user_id)
    user_object_id = to_object_id(user_id)
    member = next((m for m in document["members"] if m["user_id"] == user_object_id), None)
    if member is None or member["role"] != "admin":
        raise NotProjectAdminError("Project admin role required")
    return document


def is_project_member(project_doc: dict[str, Any], user_id: str) -> bool:
    target = to_object_id(user_id)
    return any(m["user_id"] == target for m in project_doc.get("members", []))


def is_project_admin(project_doc: dict[str, Any], user_id: str) -> bool:
    target = to_object_id(user_id)
    member = next((m for m in project_doc.get("members", []) if m["user_id"] == target), None)
    return member is not None and member["role"] == "admin"


async def fetch_project_document(db: AsyncIOMotorDatabase[Any], project_id: str) -> dict[str, Any]:
    document = await db["projects"].find_one({"_id": to_object_id(project_id)})
    if document is None:
        raise ProjectNotFoundError("Project not found")
    return document


def to_response(document: dict[str, Any]) -> ProjectResponse:
    return _project_to_response(document)
