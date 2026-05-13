from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.schemas.onboarding_task import (
    OnboardingTaskCreate,
    OnboardingTaskRead,
    OnboardingTaskStatusUpdate,
)
from app.services.event_logger import log_onboarding_event
from app.services.topic_classifier import classify_topic


router = APIRouter(prefix="/tasks", tags=["Tasks"])


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
        task_type=payload.task_type,
        priority=payload.priority,
        success_criteria=payload.success_criteria,
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


@router.get("/{task_id}", response_model=OnboardingTaskRead)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.patch("/{task_id}/status", response_model=OnboardingTaskRead)
def update_task_status(
    task_id: int,
    payload: OnboardingTaskStatusUpdate,
    db: Session = Depends(get_db),
):
    task = (
        db.query(OnboardingTask)
        .options(joinedload(OnboardingTask.plan))
        .filter(OnboardingTask.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    allowed_statuses = ["todo", "in_progress", "done", "blocked"]

    if payload.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {allowed_statuses}",
        )

    old_status = task.status
    task.status = payload.status

    topic = classify_topic(
        f"{task.title} {task.description or ''} {task.task_type}"
    )

    if task.plan and task.plan.newcomer_id:
        log_onboarding_event(
            db=db,
            newcomer_id=task.plan.newcomer_id,
            user_id=None,
            event_type="task_status_changed",
            entity_type="onboarding_task",
            entity_id=task.id,
            topic=topic,
            metadata_json={
                "task_id": task.id,
                "task_title": task.title,
                "old_status": old_status,
                "new_status": payload.status,
            },
        )

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