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