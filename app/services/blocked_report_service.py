from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.blocked_report import BlockedReport
from app.models.newcomer import NewcomerProfile
from app.services.event_logger import log_onboarding_event
from app.services.llm_service import generate_answer


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
