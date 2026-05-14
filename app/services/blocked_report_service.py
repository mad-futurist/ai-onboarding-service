from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.blocked_report import BlockedReport
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_task import OnboardingTask
from app.services.event_logger import log_onboarding_event
from app.services.llm_service import generate_answer
from app.services.topic_classifier import classify_topic


def _build_suggestion_prompt(blocker_type: str, details: str | None) -> str:
    context = f"Blocker type: {blocker_type}."
    if details:
        context += f" Details: {details}"
    return (
        f"A newcomer reported being blocked. {context}\n"
        "Suggest a concise, actionable next step to unblock them (2-3 sentences max)."
    )


def create_blocked_report(
    db: Session,
    newcomer_id: int,
    blocker_type: str,
    task_id: int | None = None,
    user_id: int | None = None,
    details: str | None = None,
) -> BlockedReport:
    ai_suggestion = None
    try:
        prompt = _build_suggestion_prompt(blocker_type, details)
        ai_suggestion = generate_answer(prompt)
    except Exception:
        pass

    report = BlockedReport(
        newcomer_id=newcomer_id,
        task_id=task_id,
        user_id=user_id,
        blocker_type=blocker_type,
        details=details,
        ai_suggestion=ai_suggestion,
        status="open",
    )

    db.add(report)
    db.flush()

    if task_id:
        task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
        if task and task.status != "done":
            old_status = task.status
            task.status = "blocked"

            topic = classify_topic(
                f"{task.title} {task.description or ''} {task.task_type}"
            )
            log_onboarding_event(
                db=db,
                newcomer_id=newcomer_id,
                user_id=user_id,
                event_type="task_status_changed",
                entity_type="onboarding_task",
                entity_id=task.id,
                topic=topic,
                metadata_json={
                    "task_id": task.id,
                    "task_title": task.title,
                    "old_status": old_status,
                    "new_status": "blocked",
                    "source": "blocked_report",
                },
            )

    log_onboarding_event(
        db=db,
        newcomer_id=newcomer_id,
        user_id=user_id,
        event_type="blocked_reported",
        entity_type="blocked_report",
        entity_id=report.id,
        topic=blocker_type,
        metadata_json={"blocker_type": blocker_type, "task_id": task_id},
    )

    db.commit()
    db.refresh(report)

    return report


def resolve_blocked_report(db: Session, report_id: int) -> BlockedReport | None:
    report = db.query(BlockedReport).filter(BlockedReport.id == report_id).first()
    if not report:
        return None
    report.status = "resolved"
    report.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report


def ignore_blocked_report(db: Session, report_id: int) -> BlockedReport | None:
    report = db.query(BlockedReport).filter(BlockedReport.id == report_id).first()
    if not report:
        return None
    report.status = "ignored"
    report.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report
