from datetime import date

from pydantic import BaseModel, Field


class AIPlanGenerationRequest(BaseModel):
    newcomer_id: int
    mentor_notes: str | None = None
    document_ids: list[int] = Field(default_factory=list)
    period_label: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    goal: str | None = None


class AIPlanTaskOutput(BaseModel):
    title: str
    description: str
    week_number: int | None = None
    day_number: int | None = None
    task_type: str
    priority: str
    success_criteria: str | None = None


class AIPlanOutput(BaseModel):
    title: str
    description: str
    plan_summary: str
    first_30_days_goal: str
    days_31_60_goal: str
    days_61_90_goal: str
    mentor_focus: str
    newcomer_focus: str
    risk_areas: list[str]
    tasks: list[AIPlanTaskOutput]


class AIPlanGenerationResponse(BaseModel):
    plan_id: int
    title: str
    status: str
    generated_by_ai: bool
    mentor_approved: bool
    tasks_count: int
    used_fallback: bool

class AIPlanServiceResult(BaseModel):
    plan: AIPlanOutput
    used_fallback: bool = False
