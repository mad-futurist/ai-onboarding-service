from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.schemas.onboarding_plan import (
    OnboardingPlanCreate,
    OnboardingPlanCreateWithTasks,
    OnboardingPlanRead,
    OnboardingPlanWithTasksRead,
)
from app.schemas.onboarding_task import OnboardingTaskRead, OnboardingTaskStatusUpdate
from app.services.event_logger import log_onboarding_event
from app.services.topic_classifier import classify_topic


router = APIRouter(prefix="/onboarding-plans", tags=["Onboarding Plans"])


@router.post("/", response_model=OnboardingPlanRead)
def create_onboarding_plan(payload: OnboardingPlanCreate, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == payload.newcomer_id).first()

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    plan = OnboardingPlan(
        newcomer_id=payload.newcomer_id,
        mentor_id=payload.mentor_id,
        title=payload.title,
        description=payload.description,
        status="draft",
        generated_by_ai=False,
        mentor_approved=False,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan


@router.post("/with-tasks", response_model=OnboardingPlanWithTasksRead)
def create_onboarding_plan_with_tasks(
    payload: OnboardingPlanCreateWithTasks,
    db: Session = Depends(get_db),
):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == payload.newcomer_id).first()

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    plan = OnboardingPlan(
        newcomer_id=payload.newcomer_id,
        mentor_id=payload.mentor_id,
        title=payload.title,
        description=payload.description,
        status="draft",
        generated_by_ai=False,
        mentor_approved=False,
    )

    db.add(plan)
    db.flush()

    for task_payload in payload.tasks:
        task = OnboardingTask(
            plan_id=plan.id,
            title=task_payload.title,
            description=task_payload.description,
            week_number=task_payload.week_number,
            day_number=task_payload.day_number,
            task_type=task_payload.task_type,
            priority=task_payload.priority,
            success_criteria=task_payload.success_criteria,
            status="todo",
        )
        db.add(task)

    db.commit()
    db.refresh(plan)

    return plan


@router.get("/{plan_id}", response_model=OnboardingPlanWithTasksRead)
def get_onboarding_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    return plan


@router.patch("/{plan_id}/approve", response_model=OnboardingPlanRead)
def approve_onboarding_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    plan.status = "approved"
    plan.mentor_approved = True

    db.commit()
    db.refresh(plan)

    return plan

@router.patch("/{task_id}/status", response_model=OnboardingTaskRead)
def update_task_status(
    task_id: int,
    payload: OnboardingTaskStatusUpdate,
    db: Session = Depends(get_db),
):
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()

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