from datetime import datetime

from pydantic import BaseModel, Field

from app.models.types import TaskPriority, TaskStatus


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    assignee_id: str | None = None
    due_date: datetime | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: str | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    project_id: str
    assignee_id: str | None
    created_by: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskStatsResponse(BaseModel):
    total: int
    todo: int
    in_progress: int
    done: int
    overdue: int
