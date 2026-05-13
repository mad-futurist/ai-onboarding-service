from datetime import date, datetime
from pydantic import BaseModel


class MentorDigestGenerateRequest(BaseModel):
    mentor_id: int


class MentorDigestRead(BaseModel):
    id: int
    mentor_id: int
    week_start: date
    week_end: date
    summary: str
    highlights: list | None
    risks: list | None
    recommended_actions: list | None
    created_at: datetime

    class Config:
        from_attributes = True
