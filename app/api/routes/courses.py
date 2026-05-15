from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.newcomer import NewcomerProfile
from app.schemas.course import (
    CourseAIGenerateRequest,
    CourseCreate,
    CourseRead,
    CourseUpdate,
    CourseWithLessonsRead,
    LessonCreate,
    LessonRead,
    LessonUpdate,
)
from app.services.course_service import (
    ai_generate_lesson_body,
    ensure_lesson_body,
    create_ai_course,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/courses", tags=["Courses"])


def _normalize_role_target(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "_".join(value.strip().lower().split())
    return normalized or None


def _role_target_filter(value: str | None):
    normalized = _normalize_role_target(value)
    if not normalized:
        return Course.id == -1
    raw = (value or "").strip().lower()
    candidates = {normalized, raw}
    role_column = func.lower(Course.role_target)
    clauses = []
    for candidate in candidates:
        if not candidate:
            continue
        clauses.extend(
            [
                role_column == candidate,
                role_column.like(f"{candidate},%"),
                role_column.like(f"%,{candidate}"),
                role_column.like(f"%,{candidate},%"),
                role_column.like(f"%, {candidate}"),
                role_column.like(f"%, {candidate},%"),
            ]
        )
    return or_(*clauses) if clauses else Course.id == -1


def _public_course_filter():
    return or_(
        Course.role_target.is_(None),
        func.lower(Course.role_target) == "all",
    )


def _newcomer_course_recommendation_filter(newcomer: NewcomerProfile):
    return or_(
        Course.newcomer_id == newcomer.id,
        (
            Course.newcomer_id.is_(None)
            & _role_target_filter(newcomer.job_title)
        ),
    )


def _newcomer_course_visibility_filter(newcomer: NewcomerProfile):
    return or_(
        _newcomer_course_recommendation_filter(newcomer),
        (
            Course.newcomer_id.is_(None)
            & _public_course_filter()
        ),
    )


def _is_course_visible_to_newcomer(course: Course, newcomer: NewcomerProfile) -> bool:
    if course.status not in ("approved", "published"):
        return False
    if course.newcomer_id is not None:
        return course.newcomer_id == newcomer.id
    target = _normalize_role_target(course.role_target)
    if target in (None, "all"):
        return True
    return target == _normalize_role_target(newcomer.job_title)


# ---------------------------------------------------------------------------
# Course CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[CourseRead])
def list_courses(
    newcomer_id: int | None = None,
    mentor_id: int | None = None,
    plan_id: int | None = None,
    role_target: str | None = None,
    status: str | None = None,
    include_role_matches: bool = False,
    public_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Course)
    if newcomer_id is not None:
        newcomer = (
            db.query(NewcomerProfile)
            .filter(NewcomerProfile.id == newcomer_id)
            .first()
        )
        if include_role_matches:
            if newcomer:
                query = query.filter(_newcomer_course_recommendation_filter(newcomer))
            else:
                query = query.filter(Course.newcomer_id == newcomer_id)
        else:
            query = query.filter(Course.newcomer_id == newcomer_id)
    if mentor_id is not None:
        query = query.filter(Course.mentor_id == mentor_id)
    if plan_id is not None:
        query = query.filter(Course.plan_id == plan_id)
    if role_target:
        query = query.filter(
            Course.newcomer_id.is_(None),
            _role_target_filter(role_target),
        )
    if public_only:
        query = query.filter(
            Course.newcomer_id.is_(None),
            _public_course_filter(),
        )
    if status:
        query = query.filter(Course.status == status)
    courses = query.order_by(Course.id.desc()).all()

    if courses:
        counts = dict(
            db.query(Lesson.course_id, func.count(Lesson.id))
            .filter(Lesson.course_id.in_([c.id for c in courses]))
            .group_by(Lesson.course_id)
            .all()
        )
        for course in courses:
            course.lessons_count = counts.get(course.id, 0)  # type: ignore[attr-defined]
    return courses


@router.post("", response_model=CourseRead)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    course = Course(
        title=payload.title,
        summary=payload.summary,
        plan_id=payload.plan_id,
        newcomer_id=payload.newcomer_id,
        mentor_id=payload.mentor_id,
        role_target=_normalize_role_target(payload.role_target),
        source_document_ids=payload.source_document_ids,
        status="draft",
        generated_by_ai=False,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.post("/ai-generate", response_model=CourseWithLessonsRead)
def ai_generate_course(payload: CourseAIGenerateRequest, db: Session = Depends(get_db)):
    course = create_ai_course(
        db=db,
        prompt_hint=payload.prompt_hint,
        title=payload.title,
        mentor_id=payload.mentor_id,
        newcomer_id=payload.newcomer_id,
        plan_id=payload.plan_id,
        role_target=_normalize_role_target(payload.role_target),
        document_ids=payload.document_ids,
        lesson_count=payload.lesson_count,
    )
    course = (
        db.query(Course)
        .options(joinedload(Course.lessons))
        .filter(Course.id == course.id)
        .first()
    )
    return course


@router.get("/{course_id}", response_model=CourseWithLessonsRead)
def get_course(
    course_id: int,
    newcomer_id: int | None = None,
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .options(joinedload(Course.lessons))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if newcomer_id is not None:
        newcomer = (
            db.query(NewcomerProfile)
            .filter(NewcomerProfile.id == newcomer_id)
            .first()
        )
        if not newcomer or not _is_course_visible_to_newcomer(course, newcomer):
            raise HTTPException(status_code=404, detail="Course not found")
    course.lessons_count = len(course.lessons)  # type: ignore[attr-defined]
    return course


@router.patch("/{course_id}", response_model=CourseRead)
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "role_target":
            value = _normalize_role_target(value)
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"detail": "Course deleted", "course_id": course_id}


# ---------------------------------------------------------------------------
# Approval workflow
# ---------------------------------------------------------------------------

@router.post("/{course_id}/submit-for-approval", response_model=CourseRead)
def submit_for_approval(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.status = "pending_approval"
    db.commit()
    db.refresh(course)
    return course


@router.post("/{course_id}/approve", response_model=CourseRead)
def approve_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.status = "approved"
    course.approved_at = _utc_now()
    db.commit()
    db.refresh(course)
    return course


@router.post("/{course_id}/publish", response_model=CourseRead)
def publish_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.status not in ("approved", "published"):
        raise HTTPException(status_code=400, detail="Course must be approved before publishing")
    course.status = "published"
    course.published_at = _utc_now()
    db.commit()
    db.refresh(course)
    return course


@router.post("/{course_id}/reject", response_model=CourseRead)
def reject_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.status = "rejected"
    db.commit()
    db.refresh(course)
    return course


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------

@router.get("/{course_id}/lessons", response_model=list[LessonRead])
def list_lessons(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id)
        .order_by(Lesson.index.asc(), Lesson.id.asc())
        .all()
    )


@router.post("/{course_id}/lessons", response_model=LessonRead)
def create_lesson(course_id: int, payload: LessonCreate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    lesson = Lesson(
        course_id=course_id,
        index=payload.index,
        title=payload.title,
        body=payload.body,
        summary=payload.summary,
        infographic_url=payload.infographic_url,
        infographic_kind=payload.infographic_kind,
        infographic_source=payload.infographic_source,
        source_document_ids=payload.source_document_ids,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.post("/{course_id}/lessons/ai-generate", response_model=LessonRead)
def ai_generate_lesson(
    course_id: int,
    lesson_title: str,
    lesson_summary: str,
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    body = ai_generate_lesson_body(course=course, lesson_title=lesson_title, lesson_summary=lesson_summary)
    body = ensure_lesson_body(lesson_title, lesson_summary, body, [])
    next_index = (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id)
        .count()
    ) + 1
    lesson = Lesson(
        course_id=course_id,
        index=next_index,
        title=lesson_title,
        body=body.body,
        summary=body.summary,
        infographic_source=body.infographic_source,
        infographic_kind=body.infographic_kind or ("mermaid" if body.infographic_source else None),
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.patch("/lessons/{lesson_id}", response_model=LessonRead)
def update_lesson(lesson_id: int, payload: LessonUpdate, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    db.delete(lesson)
    db.commit()
    return {"detail": "Lesson deleted", "lesson_id": lesson_id}
