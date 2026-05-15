from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, Database
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectMemberInput,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.project_service import (
    NotProjectAdminError,
    NotProjectMemberError,
    ProjectNotFoundError,
    add_member,
    create_project,
    delete_project,
    get_project,
    list_projects_for_user,
    remove_member,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _handle_project_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, NotProjectMemberError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, NotProjectAdminError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[ProjectResponse])
async def list_projects(current_user: CurrentUser, db: Database) -> list[ProjectResponse]:
    return await list_projects_for_user(db, current_user.id)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ProjectCreateRequest, current_user: CurrentUser, db: Database
) -> ProjectResponse:
    return await create_project(
        db,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def retrieve(project_id: str, current_user: CurrentUser, db: Database) -> ProjectResponse:
    try:
        return await get_project(db, project_id, current_user.id)
    except (ProjectNotFoundError, NotProjectMemberError, ValueError) as exc:
        raise _handle_project_error(exc) from exc


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update(
    project_id: str,
    payload: ProjectUpdateRequest,
    current_user: CurrentUser,
    db: Database,
) -> ProjectResponse:
    try:
        return await update_project(
            db,
            project_id=project_id,
            user_id=current_user.id,
            name=payload.name,
            description=payload.description,
        )
    except (ProjectNotFoundError, NotProjectMemberError, NotProjectAdminError, ValueError) as exc:
        raise _handle_project_error(exc) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy(project_id: str, current_user: CurrentUser, db: Database) -> None:
    try:
        await delete_project(db, project_id=project_id, user_id=current_user.id)
    except (ProjectNotFoundError, NotProjectMemberError, NotProjectAdminError, ValueError) as exc:
        raise _handle_project_error(exc) from exc


@router.post("/{project_id}/members", response_model=ProjectResponse)
async def add_project_member(
    project_id: str,
    payload: ProjectMemberInput,
    current_user: CurrentUser,
    db: Database,
) -> ProjectResponse:
    try:
        return await add_member(
            db,
            project_id=project_id,
            requester_id=current_user.id,
            new_member_id=payload.user_id,
            role=payload.role,
        )
    except (ProjectNotFoundError, NotProjectMemberError, NotProjectAdminError, ValueError) as exc:
        raise _handle_project_error(exc) from exc


@router.delete("/{project_id}/members/{member_id}", response_model=ProjectResponse)
async def remove_project_member(
    project_id: str,
    member_id: str,
    current_user: CurrentUser,
    db: Database,
) -> ProjectResponse:
    try:
        return await remove_member(
            db,
            project_id=project_id,
            requester_id=current_user.id,
            member_id=member_id,
        )
    except (ProjectNotFoundError, NotProjectMemberError, NotProjectAdminError, ValueError) as exc:
        raise _handle_project_error(exc) from exc
