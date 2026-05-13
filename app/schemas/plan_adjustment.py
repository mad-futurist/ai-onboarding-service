from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PlanAdjustmentChange(BaseModel):
    action: str
    title: str
    description: str | None = None
    week_number: int | None = None
    day_number: int | None = None
    task_type: str = "general"
    priority: str = "medium"
    success_criteria: str | None = None


class PlanAdjustmentRead(BaseModel):
    id: int
    newcomer_id: int
    plan_id: int
    signal_id: int | None
    title: str
    reason: str
    suggested_changes: list[dict[str, Any]]
    status: str
    created_at: datetime
    reviewed_at: datetime | None
    applied_at: datetime | None

    class Config:
        from_attributes = True


class PlanAdjustmentGenerateResponse(BaseModel):
    adjustment_id: int
    newcomer_id: int
    plan_id: int
    signal_id: int | None
    title: str
    status: str
    suggested_changes_count: int


class PlanAdjustmentStatusResponse(BaseModel):
    id: int
    status: str
    reviewed_at: datetime | None
    applied_at: datetime | None

    class Config:
        from_attributes = True