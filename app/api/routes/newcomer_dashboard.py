from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.newcomer_dashboard import NewcomerDashboardResponse
from app.services.newcomer_dashboard_service import get_newcomer_dashboard


router = APIRouter(prefix="/newcomer-dashboard", tags=["Newcomer Dashboard"])


@router.get("/{newcomer_id}", response_model=NewcomerDashboardResponse)
def read_newcomer_dashboard(
    newcomer_id: int,
    db: Session = Depends(get_db),
):
    dashboard = get_newcomer_dashboard(
        db=db,
        newcomer_id=newcomer_id,
    )

    if not dashboard:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    return dashboard