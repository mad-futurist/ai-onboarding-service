from sqlalchemy.orm import Session, joinedload

from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.ai_signal import AISignal
from app.models.plan_adjustment import PlanAdjustmentSuggestion


def get_latest_plan(
    db: Session,
    newcomer_id: int,
) -> OnboardingPlan | None:
    return (
        db.query(OnboardingPlan)
        .filter(OnboardingPlan.newcomer_id == newcomer_id)
        .order_by(OnboardingPlan.id.desc())
        .first()
    )


def compute_progress_for_plan(
    db: Session,
    plan_id: int | None,
) -> dict:
    if not plan_id:
        return {
            "total_tasks": 0,
            "completed_tasks": 0,
            "blocked_tasks": 0,
            "progress_percent": 0,
        }

    tasks = (
        db.query(OnboardingTask)
        .filter(OnboardingTask.plan_id == plan_id)
        .all()
    )

    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.status == "done"])
    blocked_tasks = len([task for task in tasks if task.status == "blocked"])

    progress_percent = 0

    if total_tasks > 0:
        progress_percent = round((completed_tasks / total_tasks) * 100)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "blocked_tasks": blocked_tasks,
        "progress_percent": progress_percent,
    }


def get_latest_open_signal(
    db: Session,
    newcomer_id: int,
) -> AISignal | None:
    return (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id)
        .filter(AISignal.status == "open")
        .order_by(AISignal.score.desc(), AISignal.id.desc())
        .first()
    )


def compute_newcomer_status(
    progress: dict,
    latest_signal: AISignal | None,
) -> str:
    if progress["blocked_tasks"] > 0:
        return "blocked"

    if latest_signal and latest_signal.severity in ["high", "medium"]:
        return "needs_attention"

    return "on_track"


def build_dashboard_newcomer_item(
    db: Session,
    newcomer: NewcomerProfile,
) -> dict:
    latest_plan = get_latest_plan(db, newcomer.id)

    plan_id = latest_plan.id if latest_plan else None

    progress = compute_progress_for_plan(
        db=db,
        plan_id=plan_id,
    )

    latest_signal = get_latest_open_signal(
        db=db,
        newcomer_id=newcomer.id,
    )

    computed_status = compute_newcomer_status(
        progress=progress,
        latest_signal=latest_signal,
    )

    return {
        "newcomer_id": newcomer.id,
        "full_name": newcomer.user.full_name if newcomer.user else "Unknown",
        "job_title": newcomer.job_title,
        "seniority": newcomer.seniority,
        "team": newcomer.team,
        "start_date": newcomer.start_date,
        "onboarding_status": newcomer.onboarding_status,
        "active_plan_id": plan_id,
        "total_tasks": progress["total_tasks"],
        "completed_tasks": progress["completed_tasks"],
        "blocked_tasks": progress["blocked_tasks"],
        "progress_percent": progress["progress_percent"],
        "computed_status": computed_status,
        "latest_signal": latest_signal,
    }


def get_mentor_dashboard(
    db: Session,
    mentor_id: int | None = None,
) -> dict:
    query = (
        db.query(NewcomerProfile)
        .options(joinedload(NewcomerProfile.user))
    )

    if mentor_id:
        query = query.filter(NewcomerProfile.mentor_id == mentor_id)

    newcomers = query.order_by(NewcomerProfile.id.desc()).all()

    items = [
        build_dashboard_newcomer_item(db, newcomer)
        for newcomer in newcomers
    ]

    on_track_count = len(
        [item for item in items if item["computed_status"] == "on_track"]
    )
    needs_attention_count = len(
        [item for item in items if item["computed_status"] == "needs_attention"]
    )
    blocked_count = len(
        [item for item in items if item["computed_status"] == "blocked"]
    )

    return {
        "active_newcomers": len(items),
        "on_track_count": on_track_count,
        "needs_attention_count": needs_attention_count,
        "blocked_count": blocked_count,
        "newcomers": items,
    }


def get_newcomer_dashboard_detail(
    db: Session,
    newcomer_id: int,
) -> dict | None:
    newcomer = (
        db.query(NewcomerProfile)
        .options(joinedload(NewcomerProfile.user))
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )

    if not newcomer:
        return None

    newcomer_item = build_dashboard_newcomer_item(
        db=db,
        newcomer=newcomer,
    )

    signals = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id)
        .order_by(AISignal.id.desc())
        .all()
    )

    adjustments = (
        db.query(PlanAdjustmentSuggestion)
        .filter(PlanAdjustmentSuggestion.newcomer_id == newcomer_id)
        .order_by(PlanAdjustmentSuggestion.id.desc())
        .all()
    )

    return {
        "newcomer": newcomer_item,
        "signals": signals,
        "adjustments": adjustments,
    }