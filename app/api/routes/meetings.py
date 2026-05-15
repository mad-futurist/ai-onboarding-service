from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.scheduled_meeting import ScheduledMeeting
from app.schemas.scheduled_meeting import (
    ScheduledMeetingCreate,
    ScheduledMeetingRead,
    ScheduledMeetingUpdate,
)


router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("", response_model=list[ScheduledMeetingRead])
def list_meetings(
    newcomer_id: int | None = None,
    organizer_user_id: int | None = None,
    plan_id: int | None = None,
    task_id: int | None = None,
    signal_id: int | None = None,
    starts_from: datetime | None = Query(default=None),
    starts_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(ScheduledMeeting)
    if newcomer_id is not None:
        query = query.filter(ScheduledMeeting.newcomer_id == newcomer_id)
    if organizer_user_id is not None:
        query = query.filter(ScheduledMeeting.organizer_user_id == organizer_user_id)
    if plan_id is not None:
        query = query.filter(ScheduledMeeting.plan_id == plan_id)
    if task_id is not None:
        query = query.filter(ScheduledMeeting.task_id == task_id)
    if signal_id is not None:
        query = query.filter(ScheduledMeeting.signal_id == signal_id)
    if starts_from is not None:
        query = query.filter(ScheduledMeeting.starts_at >= starts_from)
    if starts_to is not None:
        query = query.filter(ScheduledMeeting.starts_at <= starts_to)
    return query.order_by(ScheduledMeeting.starts_at.asc()).all()


@router.post("", response_model=ScheduledMeetingRead)
def create_meeting(payload: ScheduledMeetingCreate, db: Session = Depends(get_db)):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")

    meeting = ScheduledMeeting(
        title=payload.title,
        agenda=payload.agenda,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        newcomer_id=payload.newcomer_id,
        organizer_user_id=payload.organizer_user_id,
        plan_id=payload.plan_id,
        task_id=payload.task_id,
        signal_id=payload.signal_id,
        teams_join_url=payload.teams_join_url,
        attendee_emails=payload.attendee_emails,
        status=payload.status or "proposed",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/{meeting_id}", response_model=ScheduledMeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(ScheduledMeeting).filter(ScheduledMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.patch("/{meeting_id}", response_model=ScheduledMeetingRead)
def update_meeting(meeting_id: int, payload: ScheduledMeetingUpdate, db: Session = Depends(get_db)):
    meeting = db.query(ScheduledMeeting).filter(ScheduledMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(meeting, field, value)
    if meeting.ends_at <= meeting.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    db.commit()
    db.refresh(meeting)
    return meeting


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(ScheduledMeeting).filter(ScheduledMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db.delete(meeting)
    db.commit()
    return {"detail": "Meeting deleted", "meeting_id": meeting_id}
