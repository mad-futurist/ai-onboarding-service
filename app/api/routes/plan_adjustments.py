from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.models.plan_adjustment import PlanAdjustmentSuggestion
from app.schemas.plan_adjustment import (
    PlanAdjustmentGenerateResponse,
    PlanAdjustmentRead,
    PlanAdjustmentStatusResponse,
)
from app.services.plan_adjustment_service import (
    apply_adjustment,
    approve_adjustment,
    generate_adjustment_for_period,
    generate_adjustment_from_signal,
    reject_adjustment,
)


router = APIRouter(prefix="/plan-adjustments", tags=["Plan Adjustments"])


@router.post(
    "/generate/from-signal/{signal_id}",
    response_model=PlanAdjustmentGenerateResponse,
)
def generate_plan_adjustment_from_signal(
    signal_id: int,
    db: Session = Depends(get_db),
):
    try:
        adjustment = generate_adjustment_from_signal(
            db=db,
            signal_id=signal_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return PlanAdjustmentGenerateResponse(
        adjustment_id=adjustment.id,
        newcomer_id=adjustment.newcomer_id,
        plan_id=adjustment.plan_id,
        signal_id=adjustment.signal_id,
        title=adjustment.title,
        status=adjustment.status,
        suggested_changes_count=len(adjustment.suggested_changes or []),
    )


@router.post(
    "/generate/for-period/{plan_id}",
    response_model=PlanAdjustmentRead,
)
def generate_plan_adjustment_for_period(
    plan_id: int,
    db: Session = Depends(get_db),
):
    try:
        return generate_adjustment_for_period(
            db=db,
            plan_id=plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=list[PlanAdjustmentRead])
def list_plan_adjustments(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(PlanAdjustmentSuggestion)

    if status:
        query = query.filter(PlanAdjustmentSuggestion.status == status)

    return query.order_by(PlanAdjustmentSuggestion.id.desc()).all()


@router.get("/newcomers/{newcomer_id}", response_model=list[PlanAdjustmentRead])
def list_plan_adjustments_for_newcomer(
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

    query = db.query(PlanAdjustmentSuggestion).filter(
        PlanAdjustmentSuggestion.newcomer_id == newcomer_id
    )

    if status:
        query = query.filter(PlanAdjustmentSuggestion.status == status)

    return query.order_by(PlanAdjustmentSuggestion.id.desc()).all()


@router.get("/{adjustment_id}", response_model=PlanAdjustmentRead)
def get_plan_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
):
    adjustment = (
        db.query(PlanAdjustmentSuggestion)
        .filter(PlanAdjustmentSuggestion.id == adjustment_id)
        .first()
    )

    if not adjustment:
        raise HTTPException(status_code=404, detail="Plan adjustment not found")

    return adjustment


@router.patch("/{adjustment_id}/approve", response_model=PlanAdjustmentStatusResponse)
def approve_plan_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
):
    adjustment = approve_adjustment(
        db=db,
        adjustment_id=adjustment_id,
    )

    if not adjustment:
        raise HTTPException(status_code=404, detail="Plan adjustment not found")

    return adjustment


@router.patch("/{adjustment_id}/reject", response_model=PlanAdjustmentStatusResponse)
def reject_plan_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
):
    adjustment = reject_adjustment(
        db=db,
        adjustment_id=adjustment_id,
    )

    if not adjustment:
        raise HTTPException(status_code=404, detail="Plan adjustment not found")

    return adjustment


@router.post("/{adjustment_id}/apply", response_model=PlanAdjustmentStatusResponse)
def apply_plan_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
):
    try:
        adjustment = apply_adjustment(
            db=db,
            adjustment_id=adjustment_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not adjustment:
        raise HTTPException(status_code=404, detail="Plan adjustment not found")

    return adjustment
