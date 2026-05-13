from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.ai_question import AIQuestion
from app.models.ai_signal import AISignal
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_event import OnboardingEvent
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.plan_adjustment import PlanAdjustmentSuggestion
from app.schemas.user_story import StoryEventItem, UserStoryResponse


def get_user_story(db: Session, newcomer_id: int) -> UserStoryResponse:
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )
    if not newcomer:
        raise ValueError("Newcomer not found")

    newcomer_name = newcomer.user.full_name if newcomer.user else f"Newcomer #{newcomer_id}"

    start_date = newcomer.start_date or date.today()
    onboarding_day = (date.today() - start_date).days + 1

    events: list[StoryEventItem] = []

    # OnboardingEvents
    for evt in db.query(OnboardingEvent).filter(OnboardingEvent.newcomer_id == newcomer_id).all():
        events.append(StoryEventItem(
            event_date=evt.created_at,
            event_type=evt.event_type,
            title=evt.event_type.replace("_", " ").title(),
            description=evt.topic,
            entity_type=evt.entity_type,
            entity_id=evt.entity_id,
            metadata=evt.metadata_json,
        ))

    # AI Questions
    for q in db.query(AIQuestion).filter(AIQuestion.newcomer_id == newcomer_id).all():
        events.append(StoryEventItem(
            event_date=q.created_at,
            event_type="question_asked",
            title=q.question[:100],
            description=q.answer[:150] if q.answer else None,
            entity_type="question",
            entity_id=q.id,
            metadata=None,
        ))

    # AI Signals
    for s in db.query(AISignal).filter(AISignal.newcomer_id == newcomer_id).all():
        events.append(StoryEventItem(
            event_date=s.created_at,
            event_type="signal_detected",
            title=s.title,
            description=s.description[:150],
            entity_type="signal",
            entity_id=s.id,
            metadata={"severity": s.severity, "status": s.status},
        ))

    # Blocked reports (if table exists)
    try:
        from app.models.blocked_report import BlockedReport
        for br in db.query(BlockedReport).filter(BlockedReport.newcomer_id == newcomer_id).all():
            events.append(StoryEventItem(
                event_date=br.created_at,
                event_type="blocked",
                title=f"Blocked: {br.blocker_type.replace('_', ' ')}",
                description=br.details,
                entity_type="blocked_report",
                entity_id=br.id,
                metadata={"blocker_type": br.blocker_type, "status": br.status},
            ))
    except Exception:
        pass

    # Plan adjustments
    plans = db.query(OnboardingPlan).filter(OnboardingPlan.newcomer_id == newcomer_id).all()
    plan_ids = [p.id for p in plans]
    if plan_ids:
        for adj in (
            db.query(PlanAdjustmentSuggestion)
            .filter(
                PlanAdjustmentSuggestion.newcomer_id == newcomer_id,
                PlanAdjustmentSuggestion.status == "applied",
            )
            .all()
        ):
            events.append(StoryEventItem(
                event_date=adj.applied_at or adj.created_at,
                event_type="plan_adjusted",
                title=adj.title,
                description=adj.reason[:150],
                entity_type="plan_adjustment",
                entity_id=adj.id,
                metadata={"changes_count": len(adj.suggested_changes or [])},
            ))

    events.sort(key=lambda e: e.event_date, reverse=True)

    # Progress summary
    tasks = (
        db.query(OnboardingTask).filter(OnboardingTask.plan_id.in_(plan_ids)).all()
        if plan_ids else []
    )
    open_signals_count = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id, AISignal.status == "open")
        .count()
    )

    progress_summary = {
        "completed_tasks": sum(1 for t in tasks if t.status == "done"),
        "blocked_tasks": sum(1 for t in tasks if t.status == "blocked"),
        "open_signals": open_signals_count,
        "total_questions": db.query(AIQuestion).filter(AIQuestion.newcomer_id == newcomer_id).count(),
    }

    return UserStoryResponse(
        newcomer_id=newcomer_id,
        newcomer_name=newcomer_name,
        onboarding_day=onboarding_day,
        total_events=len(events),
        events=events,
        progress_summary=progress_summary,
    )
