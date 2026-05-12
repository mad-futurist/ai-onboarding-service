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

from app.models.document import Document
from app.schemas.ai_plan import AIPlanGenerationRequest, AIPlanGenerationResponse
from app.services.ai_plan_service import generate_onboarding_plan_with_ai


router = APIRouter(prefix="/onboarding-plans", tags=["Onboarding Plans"])

@router.post("/generate", response_model=AIPlanGenerationResponse)
def generate_onboarding_plan(
    payload: AIPlanGenerationRequest,
    db: Session = Depends(get_db),
):
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == payload.newcomer_id)
        .first()
    )

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    documents = []

    if payload.document_ids:
        documents = (
            db.query(Document)
            .filter(Document.id.in_(payload.document_ids))
            .all()
        )

        found_document_ids = {document.id for document in documents}
        missing_document_ids = set(payload.document_ids) - found_document_ids

        if missing_document_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Documents not found: {sorted(missing_document_ids)}",
            )

    ai_result = generate_onboarding_plan_with_ai(
                                        newcomer=newcomer,
                                        documents=documents,
                                        mentor_notes=payload.mentor_notes,
                                        )

    ai_plan = ai_result.plan

    plan = OnboardingPlan(
        newcomer_id=newcomer.id,
        mentor_id=newcomer.mentor_id,
        title=ai_plan.title,
        description=(
            f"{ai_plan.description}\n\n"
            f"Plan summary: {ai_plan.plan_summary}\n\n"
            f"First 30 days goal: {ai_plan.first_30_days_goal}\n"
            f"Days 31-60 goal: {ai_plan.days_31_60_goal}\n"
            f"Days 61-90 goal: {ai_plan.days_61_90_goal}\n\n"
            f"Mentor focus: {ai_plan.mentor_focus}\n"
            f"Newcomer focus: {ai_plan.newcomer_focus}\n\n"
            f"Risk areas: {', '.join(ai_plan.risk_areas)}"
        ),
        status="draft",
        generated_by_ai=True,
        mentor_approved=False,
    )

    db.add(plan)
    db.flush()

    for task_output in ai_plan.tasks:
        task = OnboardingTask(
            plan_id=plan.id,
            title=task_output.title,
            description=task_output.description,
            week_number=task_output.week_number,
            day_number=task_output.day_number,
            task_type=task_output.task_type,
            priority=task_output.priority,
            success_criteria=task_output.success_criteria,
            status="todo",
        )

        db.add(task)

    newcomer.onboarding_status = "plan_generated"

    db.commit()
    db.refresh(plan)

    used_fallback=ai_result.used_fallback

    return AIPlanGenerationResponse(
        plan_id=plan.id,
        title=plan.title,
        status=plan.status,
        generated_by_ai=plan.generated_by_ai,
        mentor_approved=plan.mentor_approved,
        tasks_count=len(ai_plan.tasks),
        used_fallback=used_fallback,
    )

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