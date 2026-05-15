from datetime import datetime
from typing import Any
from pydantic import BaseModel


class TaskExample(BaseModel):
    title: str
    content: str


class TaskLink(BaseModel):
    label: str
    url: str


class OnboardingTaskCreate(BaseModel):
    title: str
    description: str | None = None
    week_number: int | None = None
    day_number: int | None = None
    week_id: int | None = None
    sprint_id: int | None = None
    task_type: str = "general"
    priority: str = "medium"
    success_criteria: str | None = None
    acceptance_criteria: str | None = None
    examples: list[TaskExample] | None = None
    links: list[TaskLink] | None = None


class OnboardingTaskPlanCreate(BaseModel):
    """Body for POST /tasks — requires plan_id."""
    plan_id: int
    title: str
    description: str | None = None
    week_number: int | None = None
    day_number: int | None = None
    week_id: int | None = None
    sprint_id: int | None = None
    task_type: str = "general"
    priority: str = "medium"
    success_criteria: str | None = None
    acceptance_criteria: str | None = None
    examples: list[TaskExample] | None = None
    links: list[TaskLink] | None = None


class OnboardingTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    week_number: int | None = None
    day_number: int | None = None
    week_id: int | None = None
    sprint_id: int | None = None
    task_type: str | None = None
    priority: str | None = None
    success_criteria: str | None = None
    acceptance_criteria: str | None = None
    examples: list[TaskExample] | None = None
    links: list[TaskLink] | None = None


class OnboardingTaskRead(BaseModel):
    id: int
    plan_id: int
    title: str
    description: str | None
    week_number: int | None
    day_number: int | None
    week_id: int | None = None
    sprint_id: int | None = None
    task_type: str
    status: str
    priority: str
    success_criteria: str | None
    acceptance_criteria: str | None = None
    examples: list[dict[str, Any]] | None = None
    links: list[dict[str, Any]] | None = None
    manually_edited_fields: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OnboardingTaskStatusUpdate(BaseModel):
    status: str
