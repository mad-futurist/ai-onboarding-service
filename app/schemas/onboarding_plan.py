from datetime import datetime
from pydantic import BaseModel

from app.schemas.onboarding_task import OnboardingTaskCreate, OnboardingTaskRead


class OnboardingPlanCreate(BaseModel):
    newcomer_id: int
    mentor_id: int | None = None
    title: str
    description: str | None = None


class OnboardingPlanRead(BaseModel):
    id: int
    newcomer_id: int
    mentor_id: int | None
    title: str
    description: str | None
    status: str
    generated_by_ai: bool
    mentor_approved: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OnboardingPlanWithTasksRead(OnboardingPlanRead):
    tasks: list[OnboardingTaskRead] = []


class OnboardingPlanCreateWithTasks(BaseModel):
    newcomer_id: int
    mentor_id: int | None = None
    title: str
    description: str | None = None
    tasks: list[OnboardingTaskCreate] = []