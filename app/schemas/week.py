from datetime import datetime
from pydantic import BaseModel


class WeekCreate(BaseModel):
    index: int = 1
    title: str
    summary: str | None = None
    goals: list[str] | None = None
    sprint_id: int | None = None


class WeekUpdate(BaseModel):
    index: int | None = None
    title: str | None = None
    summary: str | None = None
    goals: list[str] | None = None
    sprint_id: int | None = None


class WeekRead(BaseModel):
    id: int
    plan_id: int
    sprint_id: int | None
    index: int
    title: str
    summary: str | None
    goals: list[str] | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
