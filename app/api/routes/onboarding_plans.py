from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.sprint import Sprint
from app.models.week import Week
from app.schemas.onboarding_plan import (
    OnboardingPlanCreate,
    OnboardingPlanCreateWithTasks,
    OnboardingPlanRead,
    OnboardingPlanWithTasksRead,
)
from app.schemas.sprint import SprintCreate, SprintRead, SprintUpdate
from app.schemas.week import WeekCreate, WeekRead, WeekUpdate
from app.schemas.ai_plan_partial import (
    PlanRegenerateRequest,
    PlanRegenerateResponse,
)

from app.models.document import Document
from app.schemas.ai_plan import AIPlanGenerationRequest, AIPlanGenerationResponse
from app.services.ai_plan_service import generate_onboarding_plan_with_ai
from app.services.ai_plan_partial_service import (
    regenerate_week as svc_regenerate_week,
    regenerate_task as svc_regenerate_task,
)


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


# ---------------------------------------------------------------------------
# Phase 1: scope-aware regeneration
# ---------------------------------------------------------------------------

def _load_documents(db: Session, ids: list[int]) -> list[Document]:
    if not ids:
        return []
    docs = db.query(Document).filter(Document.id.in_(ids)).all()
    found = {d.id for d in docs}
    missing = set(ids) - found
    if missing:
        raise HTTPException(status_code=404, detail=f"Documents not found: {sorted(missing)}")
    return docs


@router.post("/{plan_id}/regenerate", response_model=PlanRegenerateResponse)
def regenerate_plan(
    plan_id: int,
    payload: PlanRegenerateRequest,
    db: Session = Depends(get_db),
):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    documents = _load_documents(db, payload.document_ids)

    if payload.scope == "plan":
        # Defer to the legacy full-plan generator.
        if not plan.newcomer:
            raise HTTPException(status_code=400, detail="Plan has no newcomer attached")
        ai_result = generate_onboarding_plan_with_ai(
            newcomer=plan.newcomer,
            documents=documents,
            mentor_notes=payload.mentor_notes,
        )
        ai_plan = ai_result.plan

        plan.title = ai_plan.title
        plan.description = (
            f"{ai_plan.description}\n\n"
            f"Plan summary: {ai_plan.plan_summary}\n\n"
            f"First 30 days goal: {ai_plan.first_30_days_goal}\n"
            f"Days 31-60 goal: {ai_plan.days_31_60_goal}\n"
            f"Days 61-90 goal: {ai_plan.days_61_90_goal}\n\n"
            f"Mentor focus: {ai_plan.mentor_focus}\n"
            f"Newcomer focus: {ai_plan.newcomer_focus}\n\n"
            f"Risk areas: {', '.join(ai_plan.risk_areas)}"
        )
        plan.generated_by_ai = True
        plan.mentor_approved = False
        plan.status = "draft"

        # Wipe existing tasks (consistent with full-regen intent).
        db.query(OnboardingTask).filter(OnboardingTask.plan_id == plan.id).delete()
        db.flush()

        new_task_ids: list[int] = []
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
            db.flush()
            new_task_ids.append(task.id)

        db.commit()

        return PlanRegenerateResponse(
            scope="plan",
            plan_id=plan.id,
            target_id=None,
            summary=f"Plan regenerated with {len(ai_plan.tasks)} tasks.",
            affected_task_ids=new_task_ids,
            used_fallback=ai_result.used_fallback,
        )

    if payload.scope == "week":
        if not payload.target_id:
            raise HTTPException(status_code=400, detail="target_id is required for scope=week")
        week = (
            db.query(Week)
            .filter(Week.id == payload.target_id, Week.plan_id == plan.id)
            .first()
        )
        if not week:
            raise HTTPException(status_code=404, detail="Week not found")
        result = svc_regenerate_week(
            db=db,
            plan=plan,
            week=week,
            preserve_manual_edits=payload.preserve_manual_edits,
            mentor_notes=payload.mentor_notes,
            documents=documents,
        )
        return PlanRegenerateResponse(
            scope="week",
            plan_id=plan.id,
            target_id=week.id,
            summary=result["summary"] or f"Week {week.index} regenerated.",
            affected_task_ids=result["affected_task_ids"],
            affected_week_ids=[week.id],
            used_fallback=result["used_fallback"],
        )

    if payload.scope == "task":
        if not payload.target_id:
            raise HTTPException(status_code=400, detail="target_id is required for scope=task")
        task = (
            db.query(OnboardingTask)
            .filter(
                OnboardingTask.id == payload.target_id,
                OnboardingTask.plan_id == plan.id,
            )
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        result = svc_regenerate_task(
            db=db,
            task=task,
            preserve_manual_edits=payload.preserve_manual_edits,
            mentor_notes=payload.mentor_notes,
            documents=documents,
        )
        return PlanRegenerateResponse(
            scope="task",
            plan_id=plan.id,
            target_id=task.id,
            summary=f"Task {task.id} regenerated (fields updated: {result['fields_updated']}).",
            affected_task_ids=[task.id],
            used_fallback=result["used_fallback"],
        )

    raise HTTPException(status_code=400, detail=f"Unknown scope: {payload.scope}")


# ---------------------------------------------------------------------------
# Sprints CRUD
# ---------------------------------------------------------------------------

@router.get("/{plan_id}/sprints", response_model=list[SprintRead])
def list_sprints(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")
    return (
        db.query(Sprint)
        .filter(Sprint.plan_id == plan_id)
        .order_by(Sprint.index.asc(), Sprint.id.asc())
        .all()
    )


@router.post("/{plan_id}/sprints", response_model=SprintRead)
def create_sprint(plan_id: int, payload: SprintCreate, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")
    sprint = Sprint(
        plan_id=plan_id,
        index=payload.index,
        title=payload.title,
        description=payload.description,
        start_day=payload.start_day,
        end_day=payload.end_day,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


@router.patch("/sprints/{sprint_id}", response_model=SprintRead)
def update_sprint(sprint_id: int, payload: SprintUpdate, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sprint, field, value)
    db.commit()
    db.refresh(sprint)
    return sprint


@router.delete("/sprints/{sprint_id}")
def delete_sprint(sprint_id: int, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    db.delete(sprint)
    db.commit()
    return {"detail": "Sprint deleted", "sprint_id": sprint_id}


# ---------------------------------------------------------------------------
# Weeks CRUD
# ---------------------------------------------------------------------------

@router.get("/{plan_id}/weeks", response_model=list[WeekRead])
def list_weeks(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")
    return (
        db.query(Week)
        .filter(Week.plan_id == plan_id)
        .order_by(Week.index.asc(), Week.id.asc())
        .all()
    )


@router.post("/{plan_id}/weeks", response_model=WeekRead)
def create_week(plan_id: int, payload: WeekCreate, db: Session = Depends(get_db)):
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    if payload.sprint_id is not None:
        sprint = (
            db.query(Sprint)
            .filter(Sprint.id == payload.sprint_id, Sprint.plan_id == plan_id)
            .first()
        )
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found in this plan")

    week = Week(
        plan_id=plan_id,
        sprint_id=payload.sprint_id,
        index=payload.index,
        title=payload.title,
        summary=payload.summary,
        goals=payload.goals,
    )
    db.add(week)
    db.commit()
    db.refresh(week)
    return week


@router.patch("/weeks/{week_id}", response_model=WeekRead)
def update_week(week_id: int, payload: WeekUpdate, db: Session = Depends(get_db)):
    week = db.query(Week).filter(Week.id == week_id).first()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(week, field, value)
    db.commit()
    db.refresh(week)
    return week


@router.delete("/weeks/{week_id}")
def delete_week(week_id: int, db: Session = Depends(get_db)):
    week = db.query(Week).filter(Week.id == week_id).first()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")
    db.delete(week)
    db.commit()
    return {"detail": "Week deleted", "week_id": week_id}
