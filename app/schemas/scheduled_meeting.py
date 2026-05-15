from datetime import datetime
from pydantic import BaseModel


class ScheduledMeetingCreate(BaseModel):
    title: str
    agenda: str | None = None
    starts_at: datetime
    ends_at: datetime
    newcomer_id: int | None = None
    organizer_user_id: int | None = None
    plan_id: int | None = None
    task_id: int | None = None
    signal_id: int | None = None
    teams_join_url: str | None = None
    attendee_emails: list[str] | None = None
    status: str = "proposed"


class ScheduledMeetingUpdate(BaseModel):
    title: str | None = None
    agenda: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    teams_join_url: str | None = None
    attendee_emails: list[str] | None = None
    status: str | None = None


class ScheduledMeetingRead(BaseModel):
    id: int
    title: str
    agenda: str | None
    starts_at: datetime
    ends_at: datetime
    newcomer_id: int | None
    organizer_user_id: int | None
    plan_id: int | None
    task_id: int | None
    signal_id: int | None
    teams_join_url: str | None
    attendee_emails: list[str] | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
