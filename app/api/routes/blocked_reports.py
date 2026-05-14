from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.blocked_report import BlockedReport
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.schemas.blocked_report import (
    BlockedReportCreate,
    BlockedReportRead,
    BlockedReportStatusResponse,
)
from app.services.blocked_report_service import (
    create_blocked_report,
    ignore_blocked_report,
    resolve_blocked_report,
)

router = APIRouter(prefix="/blocked-reports", tags=["Blocked Reports"])


@router.post("/", response_model=BlockedReportRead, status_code=201)
def report_blocked(payload: BlockedReportCreate, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == payload.newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    if payload.task_id:
        task = (
            db.query(OnboardingTask)
            .join(OnboardingPlan, OnboardingTask.plan_id == OnboardingPlan.id)
            .filter(
                OnboardingTask.id == payload.task_id,
                OnboardingPlan.newcomer_id == payload.newcomer_id,
            )
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found for newcomer")

    return create_blocked_report(
        db=db,
        newcomer_id=payload.newcomer_id,
        blocker_type=payload.blocker_type,
        task_id=payload.task_id,
        user_id=payload.user_id,
        details=payload.details,
    )


@router.get("/", response_model=list[BlockedReportRead])
def list_blocked_reports(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(BlockedReport)
    if status:
        query = query.filter(BlockedReport.status == status)
    return query.order_by(BlockedReport.id.desc()).all()


@router.get("/newcomers/{newcomer_id}", response_model=list[BlockedReportRead])
def list_blocked_reports_for_newcomer(
    newcomer_id: int,
    db: Session = Depends(get_db),
):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    return (
        db.query(BlockedReport)
        .filter(BlockedReport.newcomer_id == newcomer_id)
        .order_by(BlockedReport.id.desc())
        .all()
    )


@router.get("/{report_id}", response_model=BlockedReportRead)
def get_blocked_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(BlockedReport).filter(BlockedReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Blocked report not found")
    return report


@router.patch("/{report_id}/resolve", response_model=BlockedReportStatusResponse)
def resolve_report(report_id: int, db: Session = Depends(get_db)):
    report = resolve_blocked_report(db=db, report_id=report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Blocked report not found")
    return report


@router.patch("/{report_id}/ignore", response_model=BlockedReportStatusResponse)
def ignore_report(report_id: int, db: Session = Depends(get_db)):
    report = ignore_blocked_report(db=db, report_id=report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Blocked report not found")
    return report
