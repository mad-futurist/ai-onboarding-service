from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lesson import Lesson
from app.models.newcomer import NewcomerProfile
from app.schemas.lesson_note import LessonNoteRead, LessonNoteUpsert
from app.services import lesson_note_service


router = APIRouter(prefix="/lesson-notes", tags=["Lesson Notes"])


def _ensure_refs(db: Session, newcomer_id: int, lesson_id: int) -> None:
    if not db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first():
        raise HTTPException(status_code=404, detail="Newcomer not found")
    if not db.query(Lesson).filter(Lesson.id == lesson_id).first():
        raise HTTPException(status_code=404, detail="Lesson not found")


@router.get(
    "/newcomers/{newcomer_id}/lessons/{lesson_id}",
    response_model=LessonNoteRead | None,
)
def get_lesson_note(
    newcomer_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
):
    _ensure_refs(db, newcomer_id, lesson_id)
    return lesson_note_service.get_note(db, newcomer_id, lesson_id)


@router.put(
    "/newcomers/{newcomer_id}/lessons/{lesson_id}",
    response_model=LessonNoteRead,
)
def upsert_lesson_note(
    newcomer_id: int,
    lesson_id: int,
    payload: LessonNoteUpsert,
    db: Session = Depends(get_db),
):
    _ensure_refs(db, newcomer_id, lesson_id)
    return lesson_note_service.upsert_note(
        db,
        newcomer_id=newcomer_id,
        lesson_id=lesson_id,
        body=payload.body,
    )


@router.delete(
    "/newcomers/{newcomer_id}/lessons/{lesson_id}",
    status_code=204,
)
def delete_lesson_note(
    newcomer_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
):
    _ensure_refs(db, newcomer_id, lesson_id)
    lesson_note_service.delete_note(db, newcomer_id, lesson_id)
    return Response(status_code=204)
