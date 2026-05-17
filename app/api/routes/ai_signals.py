from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.ai_signal import AISignal
from app.models.newcomer import NewcomerProfile
from app.models.ai_signal_feedback import AISignalFeedback
from app.schemas.ai_signal import (
    AISignalCatalogGroup,
    AISignalCreate,
    AISignalDetectionResponse,
    AISignalRead,
    AISignalStatusUpdateResponse,
)
from app.schemas.ai_signal_feedback import AISignalFeedbackCreate, AISignalFeedbackRead
from app.services.ai_signal_service import (
    detect_signals_for_newcomer,
    ignore_signal,
    resolve_signal,
)
from app.services.feature_service import compute_newcomer_features
from app.services.notification_service import create_notification
from app.services.signal_catalog_service import list_signal_catalog


router = APIRouter(prefix="/ai-signals", tags=["AI Signals"])


def _truncate(value: str, limit: int = 255) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _signal_with_people(db: Session, signal_id: int) -> AISignal | None:
    return (
        db.query(AISignal)
        .options(
            joinedload(AISignal.newcomer).joinedload(NewcomerProfile.user),
            joinedload(AISignal.newcomer).joinedload(NewcomerProfile.mentor),
        )
        .filter(AISignal.id == signal_id)
        .first()
    )


def _normalized_feedback_user_id(
    signal: AISignal,
    payload: AISignalFeedbackCreate,
) -> int | None:
    newcomer = signal.newcomer
    if payload.author_role == "newcomer" and newcomer:
        return newcomer.user_id
    if payload.author_role == "mentor" and payload.user_id is None and newcomer:
        return newcomer.mentor_id
    return payload.user_id


def _author_display_name(signal: AISignal, author_role: str | None) -> str:
    newcomer = signal.newcomer
    if author_role == "newcomer":
        return (
            newcomer.user.full_name
            if newcomer and newcomer.user
            else "Newcomer"
        )
    if author_role == "mentor":
        return (
            newcomer.mentor.full_name
            if newcomer and newcomer.mentor
            else "Mentor"
        )
    return "Someone"


def _notify_signal_feedback(
    db: Session,
    *,
    signal: AISignal,
    feedback: AISignalFeedback,
) -> None:
    visibility = feedback.visibility or "mentor_only"
    if visibility == "private":
        return
    if visibility == "mentor_only" and feedback.author_role == "mentor":
        return

    newcomer = signal.newcomer
    if not newcomer:
        return

    recipient_id: int | None = None
    if feedback.author_role == "newcomer":
        recipient_id = newcomer.mentor_id
    elif feedback.author_role == "mentor":
        recipient_id = newcomer.user_id

    if recipient_id is None or recipient_id == feedback.user_id:
        return

    author_name = _author_display_name(signal, feedback.author_role)
    comment = (feedback.comment or "").strip()

    if feedback.feedback_type == "adjust_request":
        notification_type = "signal_adjustment_requested"
        title = f"{author_name} requested a plan adjustment"
        body = comment or f"Plan adjustment requested from signal: {signal.title}"
    elif feedback.feedback_type == "approve":
        notification_type = "signal_reaction"
        title = f"{author_name} approved your signal note"
        body = f"Signal: {signal.title}"
    elif feedback.feedback_type == "discuss":
        notification_type = "signal_reaction"
        title = f"{author_name} wants to discuss a signal note"
        body = f"Signal: {signal.title}"
    else:
        notification_type = "signal_comment"
        title = f"{author_name} commented on a signal"
        body = comment or f"Signal: {signal.title}"

    create_notification(
        db,
        user_id=recipient_id,
        type=notification_type,
        title=_truncate(title),
        body=body,
        related_signal_id=signal.id,
        related_signal_feedback_id=feedback.id,
    )


def _notify_new_signal(db: Session, *, signal: AISignal) -> None:
    newcomer = signal.newcomer
    if not newcomer or not newcomer.mentor_id:
        return

    create_notification(
        db,
        user_id=newcomer.mentor_id,
        type="ai_signal_detected",
        title=_truncate(f"New AI signal: {signal.title}"),
        body=signal.description or signal.suggested_action or "A new AI signal needs review.",
        related_signal_id=signal.id,
    )


@router.get("/catalog", response_model=list[AISignalCatalogGroup])
def get_signal_catalog():
    return list_signal_catalog()


@router.get("/features/newcomers/{newcomer_id}")
def get_newcomer_signal_features(
    newcomer_id: int,
    db: Session = Depends(get_db),
):
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    return compute_newcomer_features(
        db=db,
        newcomer_id=newcomer_id,
        days=7,
    )

@router.post("/", response_model=AISignalRead)
def create_ai_signal(
    payload: AISignalCreate,
    db: Session = Depends(get_db),
):
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == payload.newcomer_id)
        .first()
    )

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    signal = AISignal(
        newcomer_id=payload.newcomer_id,
        signal_type=payload.signal_type,
        severity=payload.severity,
        tone=payload.tone,
        confidence=payload.confidence,
        score=payload.score,
        title=payload.title,
        description=payload.description,
        evidence=payload.evidence,
        suggested_action=payload.suggested_action,
        status="open",
        target_scope=payload.target_scope,
        target_week_id=payload.target_week_id,
        target_task_id=payload.target_task_id,
    )

    db.add(signal)
    db.flush()
    _notify_new_signal(db, signal=signal)
    db.commit()
    db.refresh(signal)

    return signal


@router.get("/", response_model=list[AISignalRead])
def list_ai_signals(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(AISignal)

    if status:
        query = query.filter(AISignal.status == status)

    return query.order_by(AISignal.id.desc()).all()


@router.get("/me", response_model=list[AISignalRead])
def list_my_signals(
    newcomer_id: int = Query(..., description="Active newcomer id from demo context"),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    query = db.query(AISignal).filter(AISignal.newcomer_id == newcomer_id)
    if status:
        query = query.filter(AISignal.status == status)
    return query.order_by(AISignal.id.desc()).all()


@router.get("/newcomers/{newcomer_id}", response_model=list[AISignalRead])
def list_ai_signals_for_newcomer(
    newcomer_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    query = db.query(AISignal).filter(AISignal.newcomer_id == newcomer_id)

    if status:
        query = query.filter(AISignal.status == status)

    return query.order_by(AISignal.id.desc()).all()


@router.post(
    "/detect/newcomers/{newcomer_id}",
    response_model=AISignalDetectionResponse,
)
def detect_newcomer_signals(
    newcomer_id: int,
    db: Session = Depends(get_db),
):
    try:
        signals, created_count, updated_count = detect_signals_for_newcomer(
            db=db,
            newcomer_id=newcomer_id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    if created_count > 0:
        signal = (
            db.query(AISignal)
            .options(joinedload(AISignal.newcomer))
            .filter(AISignal.newcomer_id == newcomer_id)
            .order_by(AISignal.id.desc())
            .first()
        )
        if signal and signal.newcomer and signal.newcomer.mentor_id:
            create_notification(
                db,
                user_id=signal.newcomer.mentor_id,
                type="ai_signals_detected",
                title=_truncate(
                    f"{created_count} new AI signal"
                    f"{'s' if created_count > 1 else ''}"
                ),
                body=(
                    f"{signal.title}"
                    if created_count == 1
                    else f"{created_count} new AI signals need review."
                ),
                related_signal_id=signal.id,
            )
            db.commit()

    return AISignalDetectionResponse(
        newcomer_id=newcomer_id,
        created_count=created_count,
        updated_count=updated_count,
        signals=signals,
    )


@router.get("/{signal_id}", response_model=AISignalRead)
def get_ai_signal(
    signal_id: int,
    db: Session = Depends(get_db),
):
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()

    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    return signal


@router.patch("/{signal_id}/resolve", response_model=AISignalStatusUpdateResponse)
def resolve_ai_signal(
    signal_id: int,
    db: Session = Depends(get_db),
):
    signal = resolve_signal(db=db, signal_id=signal_id)

    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    return signal


@router.patch("/{signal_id}/ignore", response_model=AISignalStatusUpdateResponse)
def ignore_ai_signal(
    signal_id: int,
    db: Session = Depends(get_db),
):
    signal = ignore_signal(db=db, signal_id=signal_id)

    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    return signal


@router.post("/{signal_id}/feedback", response_model=AISignalFeedbackRead, status_code=201)
def create_signal_feedback(
    signal_id: int,
    payload: AISignalFeedbackCreate,
    db: Session = Depends(get_db),
):
    signal = _signal_with_people(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    feedback_type = payload.feedback_type or "comment"
    comment = (payload.comment or "").strip()
    if feedback_type == "comment" and not comment:
        raise HTTPException(status_code=400, detail="Comment is required.")

    feedback = AISignalFeedback(
        signal_id=signal_id,
        user_id=_normalized_feedback_user_id(signal, payload),
        feedback_type=feedback_type,
        comment=comment or None,
        visibility=payload.visibility,
        author_role=payload.author_role,
    )
    db.add(feedback)
    db.flush()
    _notify_signal_feedback(db, signal=signal, feedback=feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/feedback/", response_model=list[AISignalFeedbackRead])
def list_signal_feedbacks(db: Session = Depends(get_db)):
    return db.query(AISignalFeedback).order_by(AISignalFeedback.id.desc()).all()


# --- Comments thread (visibility-aware) ---

def _filter_visible(
    rows: list[AISignalFeedback], as_role: str, user_id: int | None
) -> list[AISignalFeedback]:
    out: list[AISignalFeedback] = []
    for fb in rows:
        v = fb.visibility or "mentor_only"
        if v == "shared":
            out.append(fb)
        elif v == "mentor_only":
            # mentor sees all mentor_only; newcomer only sees own
            if as_role == "mentor":
                out.append(fb)
            elif fb.user_id is not None and user_id is not None and fb.user_id == user_id:
                out.append(fb)
        elif v == "private":
            if fb.user_id is not None and user_id is not None and fb.user_id == user_id:
                out.append(fb)
    return out


@router.get("/{signal_id}/comments", response_model=list[AISignalFeedbackRead])
def list_signal_comments(
    signal_id: int,
    as_role: str = Query("mentor", alias="as"),
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    rows = (
        db.query(AISignalFeedback)
        .filter(AISignalFeedback.signal_id == signal_id)
        .order_by(AISignalFeedback.id.asc())
        .all()
    )
    return _filter_visible(rows, as_role=as_role, user_id=user_id)


@router.post(
    "/{signal_id}/comments",
    response_model=AISignalFeedbackRead,
    status_code=201,
)
def create_signal_comment(
    signal_id: int,
    payload: AISignalFeedbackCreate,
    db: Session = Depends(get_db),
):
    signal = _signal_with_people(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    feedback_type = payload.feedback_type or "comment"
    comment = (payload.comment or "").strip()
    if feedback_type == "comment" and not comment:
        raise HTTPException(status_code=400, detail="Comment is required.")

    feedback = AISignalFeedback(
        signal_id=signal_id,
        user_id=_normalized_feedback_user_id(signal, payload),
        feedback_type=feedback_type,
        comment=comment or None,
        visibility=payload.visibility,
        author_role=payload.author_role,
    )
    db.add(feedback)
    db.flush()
    _notify_signal_feedback(db, signal=signal, feedback=feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.patch(
    "/{signal_id}/acknowledge",
    response_model=AISignalRead,
)
def acknowledge_signal(
    signal_id: int,
    db: Session = Depends(get_db),
):
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")
    signal.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(signal)
    return signal


@router.post(
    "/{signal_id}/request-plan-adjustment",
    response_model=AISignalFeedbackRead,
    status_code=201,
)
def request_plan_adjustment(
    signal_id: int,
    payload: AISignalFeedbackCreate,
    db: Session = Depends(get_db),
):
    signal = _signal_with_people(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    comment = (payload.comment or "").strip()
    feedback = AISignalFeedback(
        signal_id=signal_id,
        user_id=signal.newcomer.user_id if signal.newcomer else payload.user_id,
        feedback_type="adjust_request",
        comment=comment or "Newcomer requests a plan adjustment from this signal.",
        visibility="shared",
        author_role="newcomer",
    )
    db.add(feedback)
    db.flush()
    _notify_signal_feedback(db, signal=signal, feedback=feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
