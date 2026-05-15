from sqlalchemy.orm import Session

from app.models.lesson_note import LessonNote


def get_note(db: Session, newcomer_id: int, lesson_id: int) -> LessonNote | None:
    return (
        db.query(LessonNote)
        .filter(
            LessonNote.newcomer_id == newcomer_id,
            LessonNote.lesson_id == lesson_id,
        )
        .first()
    )


def upsert_note(db: Session, newcomer_id: int, lesson_id: int, body: str) -> LessonNote:
    note = get_note(db, newcomer_id, lesson_id)
    if note is None:
        note = LessonNote(
            newcomer_id=newcomer_id,
            lesson_id=lesson_id,
            body=body,
        )
        db.add(note)
    else:
        note.body = body
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, newcomer_id: int, lesson_id: int) -> bool:
    note = get_note(db, newcomer_id, lesson_id)
    if note is None:
        return False
    db.delete(note)
    db.commit()
    return True
