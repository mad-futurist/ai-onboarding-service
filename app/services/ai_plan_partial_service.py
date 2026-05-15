"""Scope-aware partial regeneration of an onboarding plan.

This module provides per-week, per-task and per-field AI helpers that
live alongside the existing full-plan generator (`ai_plan_service`).
The existing flow is not changed in any way.

Manually edited fields are honored: when `preserve_manual_edits=True`,
the LLM is told which fields it must not touch *and* a service-side
merge re-applies the protected values verbatim before persistence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.week import Week
from app.schemas.ai_plan import AIPlanTaskOutput
from app.services.ai_plan_service import (
    client,
    build_documents_context,
    build_newcomer_context,
    ALLOWED_TASK_TYPES,
    ALLOWED_PRIORITIES,
)


PROMPTS_DIR = Path("app/prompts/plans")


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def _load_partial_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Structured-output schemas (LLM-facing)
# ---------------------------------------------------------------------------

class _AITaskWithId(BaseModel):
    id: int | None = None
    title: str
    description: str
    week_number: int | None = None
    day_number: int | None = None
    task_type: str
    priority: str
    success_criteria: str | None = None
    acceptance_criteria: str | None = None
    examples: list[dict[str, Any]] | None = None
    links: list[dict[str, Any]] | None = None


class _AIWeekOutput(BaseModel):
    summary: str
    goals: list[str] = Field(default_factory=list)
    tasks: list[_AITaskWithId]


class _AITaskOutput(BaseModel):
    title: str
    description: str
    week_number: int | None = None
    day_number: int | None = None
    task_type: str
    priority: str
    success_criteria: str | None = None
    acceptance_criteria: str | None = None
    examples: list[dict[str, Any]] | None = None
    links: list[dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_protected_fields(task: OnboardingTask, preserve_manual_edits: bool) -> list[str]:
    if not preserve_manual_edits:
        return []
    raw = task.manually_edited_fields or []
    if isinstance(raw, list):
        return [str(f) for f in raw]
    return []


def _mark_edited(task: OnboardingTask, fields: Iterable[str]) -> None:
    current = task.manually_edited_fields or []
    if not isinstance(current, list):
        current = []
    s = set(current)
    s.update(fields)
    task.manually_edited_fields = sorted(s)


def _normalize_type_priority(task_type: str, priority: str) -> tuple[str, str]:
    if task_type not in ALLOWED_TASK_TYPES:
        task_type = "general"
    if priority not in ALLOWED_PRIORITIES:
        priority = "medium"
    return task_type, priority


def _build_plan_context(plan: OnboardingPlan, newcomer: NewcomerProfile | None) -> str:
    parts = [f"PLAN TITLE: {plan.title}"]
    if plan.description:
        parts.append(f"PLAN DESCRIPTION:\n{plan.description}")
    if newcomer:
        parts.append(build_newcomer_context(newcomer))
    return "\n\n".join(parts)


def _serialize_task_for_prompt(task: OnboardingTask, protected_fields: list[str]) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "week_number": task.week_number,
        "day_number": task.day_number,
        "task_type": task.task_type,
        "priority": task.priority,
        "success_criteria": task.success_criteria,
        "acceptance_criteria": task.acceptance_criteria,
        "examples": task.examples,
        "links": task.links,
        "protected_fields": protected_fields,
    }


# ---------------------------------------------------------------------------
# Week regeneration
# ---------------------------------------------------------------------------

def regenerate_week(
    db: Session,
    plan: OnboardingPlan,
    week: Week,
    preserve_manual_edits: bool = True,
    mentor_notes: str | None = None,
    documents: list[Document] | None = None,
) -> dict[str, Any]:
    """Rewrite a week's summary + tasks while honoring protected fields.

    Returns a dict with `summary`, `goals`, `affected_task_ids`, `used_fallback`.
    """
    documents = documents or []
    newcomer = plan.newcomer

    tasks_in_week = (
        db.query(OnboardingTask)
        .filter(OnboardingTask.plan_id == plan.id)
        .filter(
            (OnboardingTask.week_id == week.id)
            | (OnboardingTask.week_number == week.index)
        )
        .order_by(OnboardingTask.day_number.asc().nulls_last(), OnboardingTask.id.asc())
        .all()
    )

    serialized_tasks = [
        _serialize_task_for_prompt(t, _task_protected_fields(t, preserve_manual_edits))
        for t in tasks_in_week
    ]

    system_prompt = _load_partial_prompt("week_regeneration.txt")
    user_prompt = f"""
{_build_plan_context(plan, newcomer)}

WEEK CONTEXT:
Index: {week.index}
Title: {week.title}
Summary: {week.summary or "(none)"}
Goals: {week.goals or []}

MENTOR NOTES:
{mentor_notes or "No mentor notes provided."}

EXISTING TASKS (JSON):
{json.dumps(serialized_tasks, ensure_ascii=False, indent=2)}

AVAILABLE DOCUMENTS:
{build_documents_context(documents)}

TASK TYPES ALLOWED:
- read_doc
- setup
- meet_person
- first_task
- ask_ai
- checkpoint
- hr_process
- technical_practice
- general

PRIORITY VALUES ALLOWED:
- low
- medium
- high
"""

    used_fallback = False
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "week_regeneration",
                    "schema": _AIWeekOutput.model_json_schema(),
                    "strict": True,
                }
            },
        )
        parsed = _AIWeekOutput.model_validate_json(response.output_text)
    except (ValidationError, json.JSONDecodeError, Exception):
        used_fallback = True
        parsed = _AIWeekOutput(
            summary=week.summary or f"Week {week.index} of the onboarding plan",
            goals=week.goals or [],
            tasks=[
                _AITaskWithId(
                    id=t.id,
                    title=t.title,
                    description=t.description or "",
                    week_number=t.week_number,
                    day_number=t.day_number,
                    task_type=t.task_type,
                    priority=t.priority,
                    success_criteria=t.success_criteria,
                    acceptance_criteria=t.acceptance_criteria,
                    examples=t.examples,
                    links=t.links,
                )
                for t in tasks_in_week
            ],
        )

    # Apply summary/goals to the week
    week.summary = parsed.summary
    week.goals = parsed.goals

    existing_by_id = {t.id: t for t in tasks_in_week}
    affected_task_ids: list[int] = []

    for ai_task in parsed.tasks:
        task_type, priority = _normalize_type_priority(ai_task.task_type, ai_task.priority)

        if ai_task.id and ai_task.id in existing_by_id:
            task = existing_by_id[ai_task.id]
            protected = set(_task_protected_fields(task, preserve_manual_edits))
            if "title" not in protected:
                task.title = ai_task.title
            if "description" not in protected:
                task.description = ai_task.description
            if "task_type" not in protected:
                task.task_type = task_type
            if "priority" not in protected:
                task.priority = priority
            if "success_criteria" not in protected:
                task.success_criteria = ai_task.success_criteria
            if "acceptance_criteria" not in protected:
                task.acceptance_criteria = ai_task.acceptance_criteria
            if "examples" not in protected:
                task.examples = ai_task.examples
            if "links" not in protected:
                task.links = ai_task.links
            if ai_task.day_number is not None and "day_number" not in protected:
                task.day_number = ai_task.day_number
            task.week_id = week.id
            task.week_number = week.index
            affected_task_ids.append(task.id)
        else:
            new_task = OnboardingTask(
                plan_id=plan.id,
                title=ai_task.title,
                description=ai_task.description,
                week_number=week.index,
                day_number=ai_task.day_number,
                week_id=week.id,
                task_type=task_type,
                priority=priority,
                success_criteria=ai_task.success_criteria,
                acceptance_criteria=ai_task.acceptance_criteria,
                examples=ai_task.examples,
                links=ai_task.links,
                status="todo",
            )
            db.add(new_task)
            db.flush()
            affected_task_ids.append(new_task.id)

    db.commit()

    return {
        "summary": week.summary,
        "goals": week.goals,
        "affected_task_ids": affected_task_ids,
        "used_fallback": used_fallback,
    }


# ---------------------------------------------------------------------------
# Task regeneration
# ---------------------------------------------------------------------------

def regenerate_task(
    db: Session,
    task: OnboardingTask,
    preserve_manual_edits: bool = True,
    mentor_notes: str | None = None,
    documents: list[Document] | None = None,
) -> dict[str, Any]:
    documents = documents or []
    plan = task.plan
    newcomer = plan.newcomer if plan else None

    protected = _task_protected_fields(task, preserve_manual_edits)
    protected_set = set(protected)

    system_prompt = _load_partial_prompt("task_regeneration.txt")
    user_prompt = f"""
{_build_plan_context(plan, newcomer) if plan else ""}

CURRENT TASK (JSON):
{json.dumps(_serialize_task_for_prompt(task, protected), ensure_ascii=False, indent=2)}

MENTOR NOTES:
{mentor_notes or "No mentor notes provided."}

AVAILABLE DOCUMENTS:
{build_documents_context(documents)}

PROTECTED FIELDS (must not be modified):
{protected}
"""

    used_fallback = False
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "task_regeneration",
                    "schema": _AITaskOutput.model_json_schema(),
                    "strict": True,
                }
            },
        )
        parsed = _AITaskOutput.model_validate_json(response.output_text)
    except (ValidationError, json.JSONDecodeError, Exception):
        used_fallback = True
        return {
            "task_id": task.id,
            "fields_updated": [],
            "fields_preserved": protected,
            "used_fallback": True,
        }

    task_type, priority = _normalize_type_priority(parsed.task_type, parsed.priority)
    updated: list[str] = []

    def _maybe(field: str, value: Any) -> None:
        if field in protected_set:
            return
        if getattr(task, field) != value:
            setattr(task, field, value)
            updated.append(field)

    _maybe("title", parsed.title)
    _maybe("description", parsed.description)
    _maybe("task_type", task_type)
    _maybe("priority", priority)
    _maybe("success_criteria", parsed.success_criteria)
    _maybe("acceptance_criteria", parsed.acceptance_criteria)
    _maybe("examples", parsed.examples)
    _maybe("links", parsed.links)

    db.commit()

    return {
        "task_id": task.id,
        "fields_updated": updated,
        "fields_preserved": protected,
        "used_fallback": False,
    }


# ---------------------------------------------------------------------------
# Single-field suggestion (no persistence)
# ---------------------------------------------------------------------------

def ai_suggest_task_field(
    task: OnboardingTask,
    field: str,
    instruction: str | None = None,
    documents: list[Document] | None = None,
) -> Any:
    """Generate a single field value. Never writes to the DB."""
    documents = documents or []
    system_prompt = _load_partial_prompt("task_field_suggest.txt")

    user_prompt = f"""
TASK (JSON):
{json.dumps({
    "id": task.id,
    "title": task.title,
    "description": task.description,
    "week_number": task.week_number,
    "day_number": task.day_number,
    "task_type": task.task_type,
    "priority": task.priority,
    "success_criteria": task.success_criteria,
    "acceptance_criteria": task.acceptance_criteria,
    "examples": task.examples,
    "links": task.links,
}, ensure_ascii=False, indent=2)}

TARGET FIELD: {field}

MENTOR INSTRUCTION:
{instruction or "(none)"}

AVAILABLE DOCUMENTS:
{build_documents_context(documents)}
"""

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.output_text.strip()
    except Exception:
        return _fallback_field_suggestion(task, field)

    if field in ("examples", "links"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return _fallback_field_suggestion(task, field)
    return text


def _fallback_field_suggestion(task: OnboardingTask, field: str) -> Any:
    if field == "acceptance_criteria":
        return (
            f"- The newcomer can complete '{task.title}' without mentor help.\n"
            f"- The mentor confirms the outcome is verifiable."
        )
    if field == "description":
        return task.description or f"Practical step toward: {task.title}."
    if field == "examples":
        return [{"title": "Example outline", "content": "Add a concrete example here."}]
    if field == "links":
        return []
    return ""


# ---------------------------------------------------------------------------
# Generate a single new task
# ---------------------------------------------------------------------------

def ai_generate_single_task(
    plan: OnboardingPlan,
    prompt_hint: str,
    week: Week | None = None,
    sprint_id: int | None = None,
    documents: list[Document] | None = None,
) -> AIPlanTaskOutput:
    documents = documents or []
    newcomer = plan.newcomer
    system_prompt = _load_partial_prompt("task_generate.txt")

    week_block = ""
    if week:
        week_block = (
            f"\nTARGET WEEK:\nIndex: {week.index}\nTitle: {week.title}\nSummary: {week.summary or '(none)'}\n"
        )

    user_prompt = f"""
{_build_plan_context(plan, newcomer)}
{week_block}
MENTOR HINT:
{prompt_hint}

AVAILABLE DOCUMENTS:
{build_documents_context(documents)}

TASK TYPES ALLOWED:
- read_doc
- setup
- meet_person
- first_task
- ask_ai
- checkpoint
- hr_process
- technical_practice
- general

PRIORITY VALUES ALLOWED:
- low
- medium
- high
"""

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "task_generate",
                    "schema": _AITaskOutput.model_json_schema(),
                    "strict": True,
                }
            },
        )
        parsed = _AITaskOutput.model_validate_json(response.output_text)
        task_type, priority = _normalize_type_priority(parsed.task_type, parsed.priority)
        return AIPlanTaskOutput(
            title=parsed.title,
            description=parsed.description,
            week_number=parsed.week_number if parsed.week_number is not None else (week.index if week else None),
            day_number=parsed.day_number,
            task_type=task_type,
            priority=priority,
            success_criteria=parsed.success_criteria,
        )
    except (ValidationError, json.JSONDecodeError, Exception):
        return AIPlanTaskOutput(
            title=prompt_hint[:80] or "New task",
            description=f"Task drafted from hint: {prompt_hint}",
            week_number=week.index if week else None,
            day_number=None,
            task_type="general",
            priority="medium",
            success_criteria="The mentor validates the outcome of this task.",
        )
