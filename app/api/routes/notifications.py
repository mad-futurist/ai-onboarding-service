from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.onboarding_task import NotificationRead
from app.services import notification_service


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    user_id: int = Query(..., description="User to fetch notifications for"),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return notification_service.list_notifications(
        db,
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
    )


@router.get("/unread-count")
def unread_count(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    return {"unread": notification_service.unread_count(db, user_id=user_id)}


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
):
    notification = notification_service.mark_read(
        db, notification_id=notification_id
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all")
def mark_all_read(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    updated = notification_service.mark_all_read(db, user_id=user_id)
    db.commit()
    return {"updated": updated}
