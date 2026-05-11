from datetime import datetime
from pydantic import BaseModel


class OnboardingTaskCreate(BaseModel):
    title: str
    description: str | None = None
    week_number: int | None = None
    day_number: int | None = None
    task_type: str = "general"
    priority: str = "medium"


class OnboardingTaskRead(BaseModel):
    id: int
    plan_id: int
    title: str
    description: str | None
    week_number: int | None
    day_number: int | None
    task_type: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OnboardingTaskStatusUpdate(BaseModel):
    status: str

