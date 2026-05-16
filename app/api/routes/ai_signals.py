from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

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
from app.services.signal_catalog_service import list_signal_catalog


router = APIRouter(prefix="/ai-signals", tags=["AI Signals"])


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
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    feedback = AISignalFeedback(
        signal_id=signal_id,
        user_id=payload.user_id,
        feedback_type=payload.feedback_type,
        comment=payload.comment,
        visibility=payload.visibility,
        author_role=payload.author_role,
    )
    db.add(feedback)
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
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    feedback = AISignalFeedback(
        signal_id=signal_id,
        user_id=payload.user_id,
        feedback_type=payload.feedback_type or "comment",
        comment=payload.comment,
        visibility=payload.visibility,
        author_role=payload.author_role,
    )
    db.add(feedback)
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
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="AI signal not found")

    feedback = AISignalFeedback(
        signal_id=signal_id,
        user_id=payload.user_id,
        feedback_type="adjust_request",
        comment=payload.comment or "Newcomer requests a plan adjustment from this signal.",
        visibility="shared",
        author_role="newcomer",
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
