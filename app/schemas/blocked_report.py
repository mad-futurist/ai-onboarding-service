from datetime import datetime
from typing import Literal
from pydantic import BaseModel

BlockerType = Literal[
    "documentation_unclear",
    "access_issue",
    "dont_know_who_to_ask",
    "task_unclear",
    "technical_error",
    "afraid_to_ask",
    "other",
]


class BlockedReportCreate(BaseModel):
    newcomer_id: int
    task_id: int | None = None
    user_id: int | None = None
    blocker_type: BlockerType
    details: str | None = None


class BlockedReportRead(BaseModel):
    id: int
    newcomer_id: int
    task_id: int | None
    user_id: int | None
    blocker_type: str
    details: str | None
    ai_suggestion: str | None
    status: str
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class BlockedReportStatusResponse(BaseModel):
    id: int
    status: str
    resolved_at: datetime | None

    class Config:
        from_attributes = True
