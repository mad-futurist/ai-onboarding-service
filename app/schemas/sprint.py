from datetime import datetime
from pydantic import BaseModel


class SprintCreate(BaseModel):
    index: int = 1
    title: str
    description: str | None = None
    start_day: int | None = None
    end_day: int | None = None


class SprintUpdate(BaseModel):
    index: int | None = None
    title: str | None = None
    description: str | None = None
    start_day: int | None = None
    end_day: int | None = None


class SprintRead(BaseModel):
    id: int
    plan_id: int
    index: int
    title: str
    description: str | None
    start_day: int | None
    end_day: int | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
