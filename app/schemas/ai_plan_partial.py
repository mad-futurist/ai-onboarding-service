from typing import Literal, Any
from pydantic import BaseModel, Field

from app.schemas.ai_plan import AIPlanTaskOutput


RegenScope = Literal["plan", "week", "task"]
TaskField = Literal["acceptance_criteria", "description", "examples", "links"]


class PlanRegenerateRequest(BaseModel):
    scope: RegenScope = "plan"
    target_id: int | None = None
    preserve_manual_edits: bool = True
    mentor_notes: str | None = None
    document_ids: list[int] = Field(default_factory=list)


class TaskAIGenerateRequest(BaseModel):
    plan_id: int
    week_id: int | None = None
    sprint_id: int | None = None
    prompt_hint: str
    document_ids: list[int] = Field(default_factory=list)


class TaskAISuggestRequest(BaseModel):
    field: TaskField
    instruction: str | None = None


class TaskAISuggestResponse(BaseModel):
    field: TaskField
    suggestion: Any


class AIWeekOutput(BaseModel):
    summary: str
    goals: list[str] = Field(default_factory=list)
    tasks: list[AIPlanTaskOutput]


class WeekRegenResult(BaseModel):
    summary: str | None
    goals: list[str] | None
    task_ids: list[int]
    used_fallback: bool = False


class TaskRegenResult(BaseModel):
    task_id: int
    fields_updated: list[str]
    fields_preserved: list[str]
    used_fallback: bool = False


class PlanRegenerateResponse(BaseModel):
    scope: RegenScope
    plan_id: int
    target_id: int | None = None
    summary: str
    affected_task_ids: list[int] = Field(default_factory=list)
    affected_week_ids: list[int] = Field(default_factory=list)
    used_fallback: bool = False
