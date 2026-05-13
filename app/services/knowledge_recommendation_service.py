from sqlalchemy.orm import Session

from app.models.ai_question import AIQuestion
from app.models.ai_signal import AISignal
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask


def get_recommendations(db: Session, newcomer_id: int) -> list[dict]:
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise ValueError("Newcomer not found")

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
        if plan_ids else []
    )

    open_signals = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id, AISignal.status == "open")
        .all()
    )

    recent_questions = (
        db.query(AIQuestion)
        .filter(AIQuestion.newcomer_id == newcomer_id)
        .order_by(AIQuestion.id.desc())
        .limit(10)
        .all()
    )

    keywords: set[str] = set()
    for task in open_tasks:
        keywords.add(task.task_type.lower())
        for word in (task.title or "").lower().split():
            if len(word) > 4:
                keywords.add(word)
    for signal in open_signals:
        keywords.add(signal.signal_type.replace("_friction", "").replace("_confusion", ""))
    for q in recent_questions:
        for word in q.question.lower().split():
            if len(word) > 5:
                keywords.add(word)

    all_docs = db.query(Document).all()
    scored: list[tuple[Document, int, str]] = []

    for doc in all_docs:
        doc_text = f"{doc.title} {doc.document_type or ''} {doc.domain or ''} {doc.role_target or ''}".lower()
        matches = [kw for kw in keywords if kw in doc_text]
        if matches:
            scored.append((doc, len(matches), f"Relevant to: {', '.join(matches[:3])}"))

    scored.sort(key=lambda x: -x[1])

    return [
        {"document": doc, "priority": score, "reason": reason}
        for doc, score, reason in scored[:8]
    ]
