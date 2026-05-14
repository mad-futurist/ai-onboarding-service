from datetime import date, datetime
from pydantic import BaseModel, EmailStr


class NewcomerCreate(BaseModel):
    email: EmailStr
    full_name: str
    job_title: str
    seniority: str
    team: str
    start_date: date | None = None
    mentor_id: int | None = None


class NewcomerRead(BaseModel):
    id: int
    user_id: int
    mentor_id: int | None
    full_name: str | None = None
    email: EmailStr | None = None
    job_title: str
    seniority: str
    team: str
    start_date: date | None
    onboarding_status: str
    created_at: datetime

    class Config:
        from_attributes = True
