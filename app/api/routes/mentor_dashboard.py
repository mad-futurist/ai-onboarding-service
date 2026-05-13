from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.mentor_dashboard import (
    MentorDashboardResponse,
    NewcomerDashboardDetail,
)
from app.services.mentor_dashboard_service import (
    get_mentor_dashboard,
    get_newcomer_dashboard_detail,
)


router = APIRouter(prefix="/mentor-dashboard", tags=["Mentor Dashboard"])


@router.get("/", response_model=MentorDashboardResponse)
def read_mentor_dashboard(
    mentor_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_mentor_dashboard(
        db=db,
        mentor_id=mentor_id,
    )


@router.get("/newcomers/{newcomer_id}", response_model=NewcomerDashboardDetail)
def read_newcomer_dashboard_detail(
    newcomer_id: int,
    db: Session = Depends(get_db),
):
    dashboard = get_newcomer_dashboard_detail(
        db=db,
        newcomer_id=newcomer_id,
    )

    if not dashboard:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    return dashboard