from datetime import datetime
from typing import Any
from pydantic import BaseModel


class StoryEventItem(BaseModel):
    event_date: datetime
    event_type: str
    title: str
    description: str | None
    entity_type: str | None
    entity_id: int | None
    metadata: dict[str, Any] | None


class UserStoryResponse(BaseModel):
    newcomer_id: int
    newcomer_name: str
    onboarding_day: int
    total_events: int
    events: list[StoryEventItem]
    progress_summary: dict[str, Any]
