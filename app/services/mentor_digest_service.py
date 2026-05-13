from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.models.mentor_digest import MentorDigest
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.plan_adjustment import PlanAdjustmentSuggestion
from app.models.user import User


def generate_mentor_digest(db: Session, mentor_id: int) -> MentorDigest:
    mentor = db.query(User).filter(User.id == mentor_id).first()
    if not mentor:
        raise ValueError("Mentor not found")

    newcomers = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.mentor_id == mentor_id)
        .all()
    )

    newcomer_ids = [n.id for n in newcomers]

    week_end = date.today()
    week_start = week_end - timedelta(days=7)
    week_start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)

    highlights = []
    risks = []
    recommended_actions = []

    total_completed = 0
    total_open_signals = 0

    for newcomer in newcomers:
        plans = db.query(OnboardingPlan).filter(OnboardingPlan.newcomer_id == newcomer.id).all()
        plan_ids = [p.id for p in plans]

        if plan_ids:
            completed = (
                db.query(OnboardingTask)
                .filter(
                    OnboardingTask.plan_id.in_(plan_ids),
                    OnboardingTask.status == "done",
                )
                .count()
            )
            total_completed += completed

        open_signals = (
            db.query(AISignal)
            .filter(
                AISignal.newcomer_id == newcomer.id,
                AISignal.status == "open",
            )
            .all()
        )
        total_open_signals += len(open_signals)

        if open_signals:
            risks.append({
                "newcomer": newcomer.user.full_name if newcomer.user else f"#{newcomer.id}",
                "signals": [s.title for s in open_signals],
            })
            for signal in open_signals:
                recommended_actions.append(signal.suggested_action)

        highlights.append({
            "newcomer": newcomer.user.full_name if newcomer.user else f"#{newcomer.id}",
            "team": newcomer.team,
            "status": newcomer.onboarding_status,
            "open_signals": len(open_signals),
        })

    pending_adjustments = (
        db.query(PlanAdjustmentSuggestion)
        .filter(
            PlanAdjustmentSuggestion.newcomer_id.in_(newcomer_ids),
            PlanAdjustmentSuggestion.status == "pending",
        )
        .count()
    )

    summary = (
        f"Week of {week_start} — {week_end}. "
        f"{len(newcomers)} active newcomer(s). "
        f"{total_completed} task(s) completed this period. "
        f"{total_open_signals} open AI signal(s). "
        f"{pending_adjustments} pending plan adjustment(s)."
    )

    digest = MentorDigest(
        mentor_id=mentor_id,
        week_start=week_start,
        week_end=week_end,
        summary=summary,
        highlights=highlights,
        risks=risks,
        recommended_actions=list(set(recommended_actions))[:5],
    )

    db.add(digest)
    db.commit()
    db.refresh(digest)

    return digest
