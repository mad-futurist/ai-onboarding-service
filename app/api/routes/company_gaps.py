from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.company_onboarding_gap import CompanyOnboardingGap
from app.schemas.company_onboarding_gap import (
    CompanyOnboardingGapDetectResponse,
    CompanyOnboardingGapRead,
    CompanyOnboardingGapStatusResponse,
)
from app.services.company_gap_service import detect_company_gaps

router = APIRouter(prefix="/company-gaps", tags=["Company Onboarding Gaps"])


@router.get("/", response_model=list[CompanyOnboardingGapRead])
def list_company_gaps(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CompanyOnboardingGap)
    if status:
        query = query.filter(CompanyOnboardingGap.status == status)
    return query.order_by(CompanyOnboardingGap.affected_newcomers_count.desc()).all()


@router.post("/detect", response_model=CompanyOnboardingGapDetectResponse)
def detect_gaps(db: Session = Depends(get_db)):
    gaps, created, updated = detect_company_gaps(db=db)
    return CompanyOnboardingGapDetectResponse(
        gaps_created=created,
        gaps_updated=updated,
        gaps=gaps,
    )


@router.patch("/{gap_id}/resolve", response_model=CompanyOnboardingGapStatusResponse)
def resolve_gap(gap_id: int, db: Session = Depends(get_db)):
    gap = db.query(CompanyOnboardingGap).filter(CompanyOnboardingGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=404, detail="Company gap not found")
    gap.status = "resolved"
    db.commit()
    db.refresh(gap)
    return gap
