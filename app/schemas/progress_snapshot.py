from datetime import datetime
from pydantic import BaseModel


class ProgressSnapshotRead(BaseModel):
    id: int
    newcomer_id: int
    week_number: int
    completed_tasks: int
    blocked_tasks: int
    open_signals: int
    progress_percent: int
    strengths: list | None
    gaps: list | None
    mentor_notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True
