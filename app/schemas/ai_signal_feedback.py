from datetime import datetime
from typing import Literal
from pydantic import BaseModel

SignalFeedbackType = Literal[
    "useful",
    "not_relevant",
    "false_positive",
    "already_handled",
    "needs_more_context",
    "comment",
    "adjust_request",
    "approve",
    "discuss",
]

Visibility = Literal["private", "mentor_only", "shared"]
AuthorRole = Literal["mentor", "newcomer"]


class AISignalFeedbackCreate(BaseModel):
    user_id: int | None = None
    feedback_type: SignalFeedbackType = "comment"
    comment: str | None = None
    visibility: Visibility = "mentor_only"
    author_role: AuthorRole | None = None


class AISignalFeedbackRead(BaseModel):
    id: int
    signal_id: int
    user_id: int | None
    feedback_type: str
    comment: str | None
    visibility: str = "mentor_only"
    author_role: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
