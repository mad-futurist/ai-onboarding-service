from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.person_contact import PersonContact, NewcomerRecommendedContact


def get_recommended_contacts(
    db: Session,
    newcomer_id: int,
) -> list[dict]:
    open_signals = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id, AISignal.status == "open")
        .all()
    )

    plans = db.query(OnboardingPlan).filter(OnboardingPlan.newcomer_id == newcomer_id).all()
    plan_ids = [p.id for p in plans]
    open_tasks = (
        db.query(OnboardingTask)
        .filter(
            OnboardingTask.plan_id.in_(plan_ids),
            OnboardingTask.status.in_(["todo", "in_progress", "blocked"]),
        )
        .limit(10)
        .all()
    )

    relevant_topics: set[str] = set()
    for signal in open_signals:
        relevant_topics.add(signal.signal_type)
    for task in open_tasks:
        relevant_topics.add(task.task_type)

    contacts = db.query(PersonContact).filter(PersonContact.is_active == True).all()

    results = []
    for contact in contacts:
        contact_topics = contact.topics or []
        matched = [t for t in contact_topics if any(rt in t or t in rt for rt in relevant_topics)]
        if matched:
            results.append({
                "person": contact,
                "reason": f"Expert in: {', '.join(matched[:3])}",
                "topic": matched[0] if matched else None,
            })

    return results[:5]
