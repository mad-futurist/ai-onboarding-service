from datetime import date

from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.progress_snapshot import ProgressSnapshot


def generate_snapshot(db: Session, newcomer_id: int) -> ProgressSnapshot:
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise ValueError("Newcomer not found")

    plans = db.query(OnboardingPlan).filter(OnboardingPlan.newcomer_id == newcomer_id).all()
    plan_ids = [p.id for p in plans]

    tasks = (
        db.query(OnboardingTask).filter(OnboardingTask.plan_id.in_(plan_ids)).all()
        if plan_ids else []
    )

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "done")
    blocked = sum(1 for t in tasks if t.status == "blocked")
    progress_percent = int(completed / total * 100) if total > 0 else 0

    open_signals = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id, AISignal.status == "open")
        .count()
    )

    start_date = newcomer.start_date or date.today()
    days_elapsed = (date.today() - start_date).days
    week_number = max(1, (days_elapsed // 7) + 1)

    done_task_types = {t.task_type for t in tasks if t.status == "done"}
    blocked_task_types = {t.task_type for t in tasks if t.status == "blocked"}
    strengths = list(done_task_types - blocked_task_types)[:5]
    gaps = list(blocked_task_types)[:5]

    snapshot = ProgressSnapshot(
        newcomer_id=newcomer_id,
        week_number=week_number,
        completed_tasks=completed,
        blocked_tasks=blocked,
        open_signals=open_signals,
        progress_percent=progress_percent,
        strengths=strengths,
        gaps=gaps,
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
