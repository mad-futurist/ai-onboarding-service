from datetime import datetime
from pydantic import BaseModel


class AISignalRead(BaseModel):
    id: int
    newcomer_id: int
    signal_type: str
    severity: str
    tone: str = "attention"
    confidence: float
    score: float
    title: str
    description: str
    evidence: str
    suggested_action: str
    status: str
    occurrence_count: int
    target_scope: str | None = None
    target_week_id: int | None = None
    target_task_id: int | None = None
    created_at: datetime
    last_seen_at: datetime | None
    resolved_at: datetime | None
    acknowledged_at: datetime | None = None

    class Config:
        from_attributes = True


class AISignalCreate(BaseModel):
    newcomer_id: int
    signal_type: str
    severity: str = "medium"
    tone: str = "attention"
    confidence: float = 0.7
    score: float = 0.0
    title: str
    description: str
    evidence: str
    suggested_action: str
    target_scope: str | None = None
    target_week_id: int | None = None
    target_task_id: int | None = None


class AISignalDetectionResponse(BaseModel):
    newcomer_id: int
    created_count: int
    updated_count: int
    signals: list[AISignalRead]


class AISignalStatusUpdateResponse(BaseModel):
    id: int
    status: str
    resolved_at: datetime | None

    class Config:
        from_attributes = True