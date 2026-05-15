from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser, Database
from app.models.types import TaskStatus
from app.schemas.task import (
    TaskCreateRequest,
    TaskResponse,
    TaskStatsResponse,
    TaskUpdateRequest,
)
from app.services.project_service import (
    NotProjectAdminError,
    NotProjectMemberError,
    ProjectNotFoundError,
)
from app.services.task_service import (
    TaskNotFoundError,
    TaskPermissionError,
    create_task,
    delete_task,
    list_tasks,
    list_tasks_for_user,
    stats_for_user,
    update_task,
)

router = APIRouter(tags=["tasks"])


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, TaskNotFoundError) or isinstance(exc, ProjectNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (TaskPermissionError, NotProjectMemberError, NotProjectAdminError)):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
async def list_project_tasks(
    project_id: str,
    current_user: CurrentUser,
    db: Database,
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    assignee_id: str | None = None,
) -> list[TaskResponse]:
    try:
        return await list_tasks(
            db,
            project_id=project_id,
            requester_id=current_user.id,
            status=status_filter,
            assignee_id=assignee_id,
        )
    except (TaskNotFoundError, ProjectNotFoundError, TaskPermissionError, NotProjectMemberError, ValueError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_task(
    project_id: str,
    payload: TaskCreateRequest,
    current_user: CurrentUser,
    db: Database,
) -> TaskResponse:
    try:
        return await create_task(
            db,
            project_id=project_id,
            requester_id=current_user.id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            assignee_id=payload.assignee_id,
            due_date=payload.due_date,
        )
    except (ProjectNotFoundError, TaskPermissionError, NotProjectMemberError, ValueError) as exc:
        raise _map_error(exc) from exc


@router.get("/tasks/me", response_model=list[TaskResponse])
async def list_my_tasks(current_user: CurrentUser, db: Database) -> list[TaskResponse]:
    return await list_tasks_for_user(db, requester_id=current_user.id)


@router.get("/tasks/stats", response_model=TaskStatsResponse)
async def my_task_stats(current_user: CurrentUser, db: Database) -> TaskStatsResponse:
    return await stats_for_user(db, requester_id=current_user.id)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_existing_task(
    task_id: str,
    payload: TaskUpdateRequest,
    current_user: CurrentUser,
    db: Database,
) -> TaskResponse:
    updates = payload.model_dump(exclude_unset=True)
    try:
        return await update_task(
            db,
            task_id=task_id,
            requester_id=current_user.id,
            updates=updates,
        )
    except (TaskNotFoundError, TaskPermissionError, NotProjectMemberError, NotProjectAdminError, ProjectNotFoundError, ValueError) as exc:
        raise _map_error(exc) from exc


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_existing_task(
    task_id: str,
    current_user: CurrentUser,
    db: Database,
) -> None:
    try:
        await delete_task(db, task_id=task_id, requester_id=current_user.id)
    except (TaskNotFoundError, TaskPermissionError, NotProjectMemberError, NotProjectAdminError, ProjectNotFoundError, ValueError) as exc:
        raise _map_error(exc) from exc
