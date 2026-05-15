from datetime import datetime

from pydantic import BaseModel, Field

from app.models.types import ProjectMemberRole


class ProjectMemberInput(BaseModel):
    user_id: str
    role: ProjectMemberRole = "member"


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class ProjectMemberResponse(BaseModel):
    user_id: str
    role: ProjectMemberRole
    name: str | None = None
    email: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str
    members: list[ProjectMemberResponse]
    created_at: datetime
    updated_at: datetime
