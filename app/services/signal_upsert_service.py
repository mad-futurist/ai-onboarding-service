from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.services.signal_scoring_service import SignalScoreResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_signal(
    db: Session,
    newcomer_id: int,
    score_result: SignalScoreResult,
) -> tuple[AISignal, bool]:
    """
    Returns:
    - signal
    - created: True if created, False if updated
    """

    existing_signal = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id)
        .filter(AISignal.signal_type == score_result.signal_type)
        .filter(AISignal.status == "open")
        .first()
    )

    evidence_text = "\n".join(
        f"- {line}" for line in score_result.evidence_lines
    )

    if existing_signal:
        existing_signal.severity = score_result.severity
        existing_signal.confidence = score_result.confidence
        existing_signal.score = score_result.score
        existing_signal.title = score_result.title
        existing_signal.description = score_result.description
        existing_signal.evidence = evidence_text
        existing_signal.suggested_action = score_result.suggested_action
        existing_signal.occurrence_count += 1
        existing_signal.last_seen_at = utc_now()

        db.flush()

        return existing_signal, False

    signal = AISignal(
        newcomer_id=newcomer_id,
        signal_type=score_result.signal_type,
        severity=score_result.severity,
        confidence=score_result.confidence,
        score=score_result.score,
        title=score_result.title,
        description=score_result.description,
        evidence=evidence_text,
        suggested_action=score_result.suggested_action,
        status="open",
        occurrence_count=1,
        last_seen_at=utc_now(),
    )

    db.add(signal)
    db.flush()

    return signal, True