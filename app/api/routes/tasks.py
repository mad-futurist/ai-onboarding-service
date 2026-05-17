from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.task_comment import TaskComment
from app.models.week import Week
from app.schemas.document import DocumentListItem
from app.schemas.ai_question import AIQuestionRead
from app.schemas.onboarding_task import (
    NotificationRead,
    OnboardingTaskCreate,
    OnboardingTaskPlanCreate,
    OnboardingTaskRead,
    OnboardingTaskStatusUpdate,
    OnboardingTaskUpdate,
    TaskCommentCreate,
    TaskCommentRead,
)
from app.services.notification_service import create_notification
from app.schemas.ai_plan_partial import (
    TaskAIGenerateRequest,
    TaskAISuggestRequest,
    TaskAISuggestResponse,
)
from app.services.event_logger import log_onboarding_event
from app.services.task_detail_service import get_task_detail
from app.services.topic_classifier import classify_topic
from app.services.ai_plan_partial_service import (
    ai_suggest_task_field as svc_ai_suggest_task_field,
    ai_generate_single_task as svc_ai_generate_single_task,
)
from pydantic import BaseModel
from typing import Any


class TaskDetailResponse(BaseModel):
    task: OnboardingTaskRead
    why_it_matters: str | None
    related_documents: list[DocumentListItem]
    related_ai_questions: list[AIQuestionRead]
    people_to_ask: list[Any]
    suggested_prompt: str | None
    blocked_report_status: str | None


router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ---------------------------------------------------------------------------
# Legacy endpoint (kept for backwards compatibility)
# ---------------------------------------------------------------------------

@router.post("/plans/{plan_id}", response_model=OnboardingTaskRead)
def create_task_for_plan(
    plan_id: int,
    payload: OnboardingTaskCreate,
    db: Session = Depends(get_db),
):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    task = OnboardingTask(
        plan_id=plan_id,
        title=payload.title,
        description=payload.description,
        week_number=payload.week_number,
        day_number=payload.day_number,
        week_id=payload.week_id,
        sprint_id=payload.sprint_id,
        task_type=payload.task_type,
        priority=payload.priority,
        success_criteria=payload.success_criteria,
        acceptance_criteria=payload.acceptance_criteria,
        examples=[e.model_dump() for e in payload.examples] if payload.examples else None,
        links=[l.model_dump() for l in payload.links] if payload.links else None,
        status="todo",
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


@router.get("/plans/{plan_id}", response_model=list[OnboardingTaskRead])
def list_tasks_for_plan(
    plan_id: int,
    db: Session = Depends(get_db),
):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    return (
        db.query(OnboardingTask)
        .filter(OnboardingTask.plan_id == plan_id)
        .order_by(
            OnboardingTask.week_number.asc().nulls_last(),
            OnboardingTask.day_number.asc().nulls_last(),
            OnboardingTask.id.asc(),
        )
        .all()
    )


# ---------------------------------------------------------------------------
# Phase 1: scoped create + AI helpers + partial PATCH
# ---------------------------------------------------------------------------

@router.post("", response_model=OnboardingTaskRead)
def create_task(payload: OnboardingTaskPlanCreate, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    week_index_for_task = payload.week_number
    if payload.week_id is not None:
        week = (
            db.query(Week)
            .filter(Week.id == payload.week_id, Week.plan_id == plan.id)
            .first()
        )
        if not week:
            raise HTTPException(status_code=404, detail="Week not found in this plan")
        # Keep both representations in sync for legacy readers.
        if week_index_for_task is None:
            week_index_for_task = week.index

    task = OnboardingTask(
        plan_id=plan.id,
        title=payload.title,
        description=payload.description,
        week_number=week_index_for_task,
        day_number=payload.day_number,
        week_id=payload.week_id,
        sprint_id=payload.sprint_id,
        task_type=payload.task_type,
        priority=payload.priority,
        success_criteria=payload.success_criteria,
        acceptance_criteria=payload.acceptance_criteria,
        examples=[e.model_dump() for e in payload.examples] if payload.examples else None,
        links=[l.model_dump() for l in payload.links] if payload.links else None,
        status="todo",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.post("/ai-generate", response_model=OnboardingTaskRead)
def ai_generate_task(payload: TaskAIGenerateRequest, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    week = None
    if payload.week_id is not None:
        week = (
            db.query(Week)
            .filter(Week.id == payload.week_id, Week.plan_id == plan.id)
            .first()
        )
        if not week:
            raise HTTPException(status_code=404, detail="Week not found in this plan")

    documents: list[Document] = []
    if payload.document_ids:
        documents = db.query(Document).filter(Document.id.in_(payload.document_ids)).all()

    ai_task = svc_ai_generate_single_task(
        plan=plan,
        prompt_hint=payload.prompt_hint,
        week=week,
        sprint_id=payload.sprint_id,
        documents=documents,
    )

    week_number_for_task = ai_task.week_number
    if week_number_for_task is None and week is not None:
        week_number_for_task = week.index

    task = OnboardingTask(
        plan_id=plan.id,
        title=ai_task.title,
        description=ai_task.description,
        week_number=week_number_for_task,
        day_number=ai_task.day_number,
        week_id=week.id if week else None,
        sprint_id=payload.sprint_id,
        task_type=ai_task.task_type,
        priority=ai_task.priority,
        success_criteria=ai_task.success_criteria,
        status="todo",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/ai-suggest", response_model=TaskAISuggestResponse)
def ai_suggest_task_field(
    task_id: int,
    payload: TaskAISuggestRequest,
    db: Session = Depends(get_db),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    suggestion = svc_ai_suggest_task_field(
        task=task,
        field=payload.field,
        instruction=payload.instruction,
    )
    return TaskAISuggestResponse(field=payload.field, suggestion=suggestion)


@router.get("/{task_id}/detail")
def get_task_detail_view(task_id: int, db: Session = Depends(get_db)):
    detail = get_task_detail(db=db, task_id=task_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task": detail["task"],
        "why_it_matters": detail["why_it_matters"],
        "related_documents": detail["related_documents"],
        "related_ai_questions": detail["related_ai_questions"],
        "people_to_ask": detail["people_to_ask"],
        "suggested_prompt": detail["suggested_prompt"],
        "blocked_report_status": detail["blocked_report_status"],
    }


@router.get("/{task_id}", response_model=OnboardingTaskRead)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


ALLOWED_TASK_STATUSES = ["todo", "in_progress", "in_review", "done", "blocked"]

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "todo": {"in_progress", "blocked"},
    "in_progress": {"in_review", "blocked", "done", "todo"},
    "in_review": {"done", "in_progress", "blocked"},
    "blocked": {"in_progress", "todo"},
    "done": {"in_progress"},
}


@router.patch("/{task_id}/status", response_model=OnboardingTaskRead)
def update_task_status(
    task_id: int,
    payload: OnboardingTaskStatusUpdate,
    db: Session = Depends(get_db),
):
    task = (
        db.query(OnboardingTask)
        .options(
            joinedload(OnboardingTask.plan).joinedload(
                OnboardingPlan.newcomer
            )
        )
        .filter(OnboardingTask.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.status not in ALLOWED_TASK_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {ALLOWED_TASK_STATUSES}",
        )

    old_status = task.status

    if old_status != payload.status:
        allowed_next = ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
        if payload.status not in allowed_next:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid transition {old_status} -> {payload.status}. "
                    f"Allowed: {sorted(allowed_next)}"
                ),
            )

    is_return_from_review = (
        old_status == "in_review" and payload.status == "in_progress"
    )

    if is_return_from_review and not (payload.comment and payload.comment.strip()):
        raise HTTPException(
            status_code=400,
            detail="A comment is required when returning a task from review.",
        )

    task.status = payload.status

    review_comment: TaskComment | None = None
    if payload.comment and payload.comment.strip():
        review_comment = TaskComment(
            task_id=task.id,
            author_user_id=payload.actor_user_id,
            body=payload.comment.strip(),
            comment_type=(
                "review_return" if is_return_from_review else "status_change"
            ),
            from_status=old_status,
            to_status=payload.status,
        )
        db.add(review_comment)
        db.flush()

    if is_return_from_review and task.plan and task.plan.newcomer:
        newcomer = task.plan.newcomer
        if newcomer.user_id:
            create_notification(
                db,
                user_id=newcomer.user_id,
                type="task_returned_from_review",
                title=f"Task returned for changes: {task.title}",
                body=(
                    review_comment.body
                    if review_comment is not None
                    else "Your mentor returned this task for changes."
                ),
                related_task_id=task.id,
                related_comment_id=(
                    review_comment.id if review_comment is not None else None
                ),
            )

    topic = classify_topic(
        f"{task.title} {task.description or ''} {task.task_type}"
    )

    if task.plan and task.plan.newcomer_id:
        log_onboarding_event(
            db=db,
            newcomer_id=task.plan.newcomer_id,
            user_id=payload.actor_user_id,
            event_type="task_status_changed",
            entity_type="onboarding_task",
            entity_id=task.id,
            topic=topic,
            metadata_json={
                "task_id": task.id,
                "task_title": task.title,
                "old_status": old_status,
                "new_status": payload.status,
                "comment_id": review_comment.id if review_comment else None,
                "is_return_from_review": is_return_from_review,
            },
        )

    db.commit()
    db.refresh(task)

    return task


@router.get("/{task_id}/comments", response_model=list[TaskCommentRead])
def list_task_comments(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return (
        db.query(TaskComment)
        .filter(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.desc())
        .all()
    )


@router.post("/{task_id}/comments", response_model=TaskCommentRead)
def create_task_comment(
    task_id: int,
    payload: TaskCommentCreate,
    db: Session = Depends(get_db),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not payload.body or not payload.body.strip():
        raise HTTPException(status_code=400, detail="Comment body is required.")

    comment = TaskComment(
        task_id=task_id,
        author_user_id=payload.author_user_id,
        body=payload.body.strip(),
        comment_type=payload.comment_type or "general",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.patch("/{task_id}", response_model=OnboardingTaskRead)
def update_task(
    task_id: int,
    payload: OnboardingTaskUpdate,
    db: Session = Depends(get_db),
):
    """Partial update of enriched task fields.

    Each field in the payload is added to `manually_edited_fields` so that
    future scope-aware regenerations preserve the mentor's edits by default.
    """
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)
    edited: set[str] = set()

    for field, value in updates.items():
        if field in ("examples", "links") and value is not None:
            # Pydantic gave us list[TaskExample]/list[TaskLink] models — serialize.
            value = [v.model_dump() if hasattr(v, "model_dump") else v for v in value]
        setattr(task, field, value)
        edited.add(field)

    # If week_id changed and week_number wasn't explicitly given, mirror the index.
    if "week_id" in edited and "week_number" not in edited and task.week_id is not None:
        week = db.query(Week).filter(Week.id == task.week_id).first()
        if week:
            task.week_number = week.index

    current = task.manually_edited_fields or []
    if not isinstance(current, list):
        current = []
    task.manually_edited_fields = sorted(set(current) | edited)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return {
        "detail": "Task deleted successfully",
        "task_id": task_id,
    }
