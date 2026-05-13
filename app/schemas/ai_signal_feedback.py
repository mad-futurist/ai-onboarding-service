from datetime import datetime
from typing import Literal
from pydantic import BaseModel

SignalFeedbackType = Literal[
    "useful",
    "not_relevant",
    "false_positive",
    "already_handled",
    "needs_more_context",
]


class AISignalFeedbackCreate(BaseModel):
    user_id: int | None = None
    feedback_type: SignalFeedbackType
    comment: str | None = None


class AISignalFeedbackRead(BaseModel):
    id: int
    signal_id: int
    user_id: int | None
    feedback_type: str
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True
