from datetime import datetime
from pydantic import BaseModel


class AISignalRead(BaseModel):
    id: int
    newcomer_id: int
    signal_type: str
    severity: str
    confidence: float
    title: str
    description: str
    evidence: str
    suggested_action: str
    status: str
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class AISignalCreate(BaseModel):
    newcomer_id: int
    signal_type: str
    severity: str = "medium"
    confidence: float = 0.7
    title: str
    description: str
    evidence: str
    suggested_action: str


class AISignalDetectionResponse(BaseModel):
    newcomer_id: int
    created_count: int
    signals: list[AISignalRead]


class AISignalStatusUpdateResponse(BaseModel):
    id: int
    status: str
    resolved_at: datetime | None

    class Config:
        from_attributes = True