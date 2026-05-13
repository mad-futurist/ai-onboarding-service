from datetime import datetime
from pydantic import BaseModel


class OnboardingReflectionCreate(BaseModel):
    newcomer_id: int
    what_became_clear: str | None = None
    what_was_confusing: str | None = None
    most_helpful_document: str | None = None
    most_helpful_person: str | None = None
    improvement_suggestions: str | None = None


class OnboardingReflectionRead(BaseModel):
    id: int
    newcomer_id: int
    what_became_clear: str | None
    what_was_confusing: str | None
    most_helpful_document: str | None
    most_helpful_person: str | None
    improvement_suggestions: str | None
    created_at: datetime

    class Config:
        from_attributes = True
