from datetime import datetime
from typing import Literal
from pydantic import BaseModel

FeedbackType = Literal[
    "helpful",
    "not_helpful",
    "wrong_source",
    "too_generic",
    "missing_context",
    "still_blocked",
]


class AIAnswerFeedbackCreate(BaseModel):
    user_id: int | None = None
    newcomer_id: int | None = None
    rating: int | None = None
    feedback_type: FeedbackType
    comment: str | None = None


class AIAnswerFeedbackRead(BaseModel):
    id: int
    question_id: int
    user_id: int | None
    newcomer_id: int | None
    rating: int | None
    feedback_type: str
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True
