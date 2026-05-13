from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ai_signal import AISignal
from app.models.newcomer import NewcomerProfile
from app.models.ai_signal_feedback import AISignalFeedback
from app.schemas.ai_signal import (
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


router = APIRouter(prefix="/ai-signals", tags=["AI Signals"])

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
        confidence=payload.confidence,
        title=payload.title,
        description=payload.description,
        evidence=payload.evidence,
        suggested_action=payload.suggested_action,
        status="open",
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
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/feedback/", response_model=list[AISignalFeedbackRead])
def list_signal_feedbacks(db: Session = Depends(get_db)):
    return db.query(AISignalFeedback).order_by(AISignalFeedback.id.desc()).all()