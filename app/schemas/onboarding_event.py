from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OnboardingEventRead(BaseModel):
    id: int
    newcomer_id: int
    user_id: int | None
    event_type: str
    entity_type: str | None
    entity_id: int | None
    topic: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class OnboardingEventCreate(BaseModel):
    newcomer_id: int
    user_id: int | None = None
    event_type: str
    entity_type: str | None = None
    entity_id: int | None = None
    topic: str | None = None
    metadata_json: dict[str, Any] | None = None