from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.types import TaskPriority, TaskStatus, to_object_id
from app.schemas.task import TaskResponse, TaskStatsResponse
from app.services.project_service import (
    NotProjectAdminError,
    fetch_project_document,
    is_project_admin,
    is_project_member,
)


class TaskNotFoundError(Exception):
    pass


class TaskPermissionError(Exception):
    pass


def _task_to_response(document: dict[str, Any]) -> TaskResponse:
    return TaskResponse(
        id=str(document["_id"]),
        title=document["title"],
        description=document.get("description", ""),
        status=document["status"],
        priority=document["priority"],
        project_id=str(document["project_id"]),
        assignee_id=str(document["assignee_id"]) if document.get("assignee_id") else None,
        created_by=str(document["created_by"]),
        due_date=document.get("due_date"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


async def create_task(
    db: AsyncIOMotorDatabase[Any],
    *,
    project_id: str,
    requester_id: str,
    title: str,
    description: str,
    status: TaskStatus,
    priority: TaskPriority,
    assignee_id: str | None,
    due_date: datetime | None,
) -> TaskResponse:
    project = await fetch_project_document(db, project_id)
    if not is_project_member(project, requester_id):
        raise TaskPermissionError("Not a member of this project")
    if assignee_id and not is_project_member(project, assignee_id):
        raise TaskPermissionError("Assignee must be a project member")
    now = datetime.now(timezone.utc)
    document = {
        "title": title.strip(),
        "description": description.strip(),
        "status": status,
        "priority": priority,
        "project_id": project["_id"],
        "assignee_id": to_object_id(assignee_id) if assignee_id else None,
        "created_by": to_object_id(requester_id),
        "due_date": due_date,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["tasks"].insert_one(document)
    document["_id"] = result.inserted_id
    return _task_to_response(document)


async def list_tasks(
    db: AsyncIOMotorDatabase[Any],
    *,
    project_id: str,
    requester_id: str,
    status: TaskStatus | None = None,
    assignee_id: str | None = None,
) -> list[TaskResponse]:
    project = await fetch_project_document(db, project_id)
    if not is_project_member(project, requester_id):
        raise TaskPermissionError("Not a member of this project")
    query: dict[str, Any] = {"project_id": project["_id"]}
    if status:
        query["status"] = status
    if assignee_id:
        query["assignee_id"] = to_object_id(assignee_id)
    cursor = db["tasks"].find(query).sort("created_at", -1)
    return [_task_to_response(doc) async for doc in cursor]


async def list_tasks_for_user(
    db: AsyncIOMotorDatabase[Any],
    *,
    requester_id: str,
) -> list[TaskResponse]:
    requester_object_id = to_object_id(requester_id)
    projects_cursor = db["projects"].find({"members.user_id": requester_object_id}, projection={"_id": 1})
    project_ids = [doc["_id"] async for doc in projects_cursor]
    if not project_ids:
        return []
    cursor = db["tasks"].find({"project_id": {"$in": project_ids}}).sort("created_at", -1)
    return [_task_to_response(doc) async for doc in cursor]


async def update_task(
    db: AsyncIOMotorDatabase[Any],
    *,
    task_id: str,
    requester_id: str,
    updates: dict[str, Any],
) -> TaskResponse:
    task = await db["tasks"].find_one({"_id": to_object_id(task_id)})
    if task is None:
        raise TaskNotFoundError("Task not found")
    project = await fetch_project_document(db, str(task["project_id"]))
    if not is_project_member(project, requester_id):
        raise TaskPermissionError("Not a member of this project")
    requester_object_id = to_object_id(requester_id)
    is_admin = is_project_admin(project, requester_id)
    is_assignee = task.get("assignee_id") == requester_object_id
    is_creator = task.get("created_by") == requester_object_id
    restricted_fields = {"title", "description", "priority", "assignee_id", "due_date"}
    if not is_admin and not is_creator and restricted_fields.intersection(updates.keys()):
        raise TaskPermissionError("Only project admins or task creators can edit task details")
    if updates.get("assignee_id") and not is_project_member(project, updates["assignee_id"]):
        raise TaskPermissionError("Assignee must be a project member")
    if "status" in updates and not (is_admin or is_creator or is_assignee):
        raise TaskPermissionError("You can only change status of your own tasks")
    db_updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    for key, value in updates.items():
        if value is None and key not in {"assignee_id", "due_date"}:
            continue
        if key == "assignee_id":
            db_updates[key] = to_object_id(value) if value else None
        else:
            db_updates[key] = value
    await db["tasks"].update_one({"_id": task["_id"]}, {"$set": db_updates})
    refreshed = await db["tasks"].find_one({"_id": task["_id"]})
    if refreshed is None:
        raise TaskNotFoundError("Task not found")
    return _task_to_response(refreshed)


async def delete_task(db: AsyncIOMotorDatabase[Any], *, task_id: str, requester_id: str) -> None:
    task = await db["tasks"].find_one({"_id": to_object_id(task_id)})
    if task is None:
        raise TaskNotFoundError("Task not found")
    project = await fetch_project_document(db, str(task["project_id"]))
    if not is_project_admin(project, requester_id) and task.get("created_by") != to_object_id(requester_id):
        raise NotProjectAdminError("Only project admins or the task creator can delete tasks")
    await db["tasks"].delete_one({"_id": task["_id"]})


async def stats_for_user(
    db: AsyncIOMotorDatabase[Any],
    *,
    requester_id: str,
) -> TaskStatsResponse:
    tasks = await list_tasks_for_user(db, requester_id=requester_id)
    now = datetime.now(timezone.utc)
    todo = sum(1 for t in tasks if t.status == "todo")
    in_progress = sum(1 for t in tasks if t.status == "in_progress")
    done = sum(1 for t in tasks if t.status == "done")
    overdue = sum(
        1
        for t in tasks
        if t.status != "done" and t.due_date is not None and _ensure_tz(t.due_date) < now
    )
    return TaskStatsResponse(
        total=len(tasks),
        todo=todo,
        in_progress=in_progress,
        done=done,
        overdue=overdue,
    )


def _ensure_tz(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
