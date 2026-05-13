from datetime import datetime
from pydantic import BaseModel


class PersonContactCreate(BaseModel):
    full_name: str
    role: str
    team: str | None = None
    email: str | None = None
    topics: list[str] = []
    is_active: bool = True


class PersonContactRead(BaseModel):
    id: int
    full_name: str
    role: str
    team: str | None
    email: str | None
    topics: list[str] | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NewcomerRecommendedContactRead(BaseModel):
    person: PersonContactRead
    reason: str
    topic: str | None

    class Config:
        from_attributes = True
