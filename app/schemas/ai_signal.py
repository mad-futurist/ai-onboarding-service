from datetime import datetime
from pydantic import BaseModel


class AISignalRead(BaseModel):
    id: int
    newcomer_id: int
    signal_type: str
    severity: str
    confidence: float
    score: float
    title: str
    description: str
    evidence: str
    suggested_action: str
    status: str
    occurrence_count: int
    created_at: datetime
    last_seen_at: datetime | None
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class AISignalCreate(BaseModel):
    newcomer_id: int
    signal_type: str
    severity: str = "medium"
    confidence: float = 0.7
    score: float = 0.0
    title: str
    description: str
    evidence: str
    suggested_action: str


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