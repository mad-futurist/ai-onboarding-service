from sqlalchemy.orm import Session

from app.models.ai_answer_feedback import AIAnswerFeedback
from app.models.ai_question import AIQuestion
from app.services.signal_upsert_service import upsert_signal
from app.services.signal_scoring_service import SignalScoreResult

NEGATIVE_TYPES = {"not_helpful", "wrong_source", "too_generic", "missing_context", "still_blocked"}
SIGNAL_THRESHOLD = 3


def create_feedback(
    db: Session,
    question_id: int,
    feedback_type: str,
    user_id: int | None = None,
    newcomer_id: int | None = None,
    rating: int | None = None,
    comment: str | None = None,
) -> AIAnswerFeedback:
    feedback = AIAnswerFeedback(
        question_id=question_id,
        user_id=user_id,
        newcomer_id=newcomer_id,
        rating=rating,
        feedback_type=feedback_type,
        comment=comment,
    )

    db.add(feedback)
    db.flush()

    if newcomer_id and feedback_type in NEGATIVE_TYPES:
        _check_and_trigger_signal(db, newcomer_id)

    db.commit()
    db.refresh(feedback)
    return feedback


def _check_and_trigger_signal(db: Session, newcomer_id: int) -> None:
    negative_count = (
        db.query(AIAnswerFeedback)
        .filter(
            AIAnswerFeedback.newcomer_id == newcomer_id,
            AIAnswerFeedback.feedback_type.in_(NEGATIVE_TYPES),
        )
        .count()
    )

    if negative_count >= SIGNAL_THRESHOLD:
        score_result = SignalScoreResult(
            signal_type="knowledge_friction",
            topic="knowledge_base",
            score=min(0.9, 0.7 + (negative_count - SIGNAL_THRESHOLD) * 0.05),
            severity="medium",
            tone="attention",
            confidence=0.8,
            title="AI answers not meeting newcomer needs",
            description=(
                f"The newcomer gave {negative_count} negative feedback(s) on AI answers. "
                "This may indicate the knowledge base lacks relevant or actionable content."
            ),
            evidence_lines=[f"{negative_count} negative AI answer feedbacks recorded."],
            suggested_action=(
                "Review the most-used documents and improve their clarity. "
                "Consider adding role-specific quick-reference guides."
            ),
        )
        upsert_signal(db=db, newcomer_id=newcomer_id, score_result=score_result)
