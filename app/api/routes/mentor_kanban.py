from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.mentor_kanban_service import get_mentor_kanban


router = APIRouter(prefix="/mentor", tags=["Mentor Kanban"])


@router.get("/{mentor_id}/kanban")
def fetch_mentor_kanban(
    mentor_id: int,
    statuses: str | None = Query(
        None,
        description="Comma separated list of statuses to include",
    ),
    newcomer_id: int | None = Query(None),
    priority: str | None = Query(None),
    task_type: str | None = Query(None),
    has_open_signal: bool | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    parsed_statuses = (
        [s.strip() for s in statuses.split(",") if s.strip()]
        if statuses
        else None
    )
    return get_mentor_kanban(
        db,
        mentor_id=mentor_id,
        statuses=parsed_statuses,
        newcomer_id=newcomer_id,
        priority=priority,
        task_type=task_type,
        has_open_signal=has_open_signal,
        search=search,
    )
