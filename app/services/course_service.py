"""Basic course / lesson generation built on the existing OpenAI plumbing.

Phase 1b: lessons are produced one by one with simple structured output.
Infographic generation is opt-in via Mermaid source text only — no external
rendering service is contacted from the backend; the frontend can choose to
render via mermaid.ink or kroki later.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.course import Course
from app.models.document import Document
from app.models.lesson import Lesson
from app.models.newcomer import NewcomerProfile
from app.services.ai_plan_service import (
    client,
    build_documents_context,
    build_newcomer_context,
)


PROMPTS_DIR = Path("app/prompts/courses")


def _load(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# LLM schemas
# ---------------------------------------------------------------------------

class _AILessonOutline(BaseModel):
    title: str
    summary: str


class _AICourseOutline(BaseModel):
    title: str
    summary: str
    lessons: list[_AILessonOutline] = Field(default_factory=list)


class _AILessonBody(BaseModel):
    body: str
    summary: str
    infographic_source: str | None = None
    infographic_kind: str | None = None


def _fallback_lesson_outlines(prompt_hint: str, lesson_count: int) -> list[_AILessonOutline]:
    topic = (prompt_hint or "the onboarding topic").strip()
    templates = [
        (f"Understand {topic}", f"Get the essential context, vocabulary, and expected outcome for {topic}."),
        ("Map the workflow", f"Learn the step-by-step process, key handoffs, and source materials for {topic}."),
        ("Practice with mentor support", f"Apply {topic} in a guided task and capture questions before working alone."),
        ("Work independently", f"Use a checklist to complete a small {topic} task with confidence."),
    ]
    if lesson_count > len(templates):
        templates.extend(
            (
                f"Deepen topic {i + 1}",
                f"Review a more advanced scenario for {topic} and capture remaining questions.",
            )
            for i in range(len(templates), lesson_count)
        )
    return [_AILessonOutline(title=title[:120], summary=summary) for title, summary in templates[:lesson_count]]


def _fallback_lesson_body(lesson_title: str, lesson_summary: str, documents: list[Document]) -> _AILessonBody:
    source_titles = [doc.title for doc in documents[:3]]
    source_line = ", ".join(source_titles) if source_titles else "the mentor-approved onboarding materials"
    body = (
        f"## {lesson_title}\n\n"
        f"{lesson_summary}\n\n"
        "### What to learn\n\n"
        f"- Read the relevant source material: {source_line}.\n"
        "- Identify the terms, tools, and people involved.\n"
        "- Write down one thing that is clear and one thing that still needs clarification.\n\n"
        "### How to practice\n\n"
        "- Walk through the workflow with your mentor or the recommended teammate.\n"
        "- Try the smallest safe version of the task yourself.\n"
        "- Compare your result with the checklist or success criteria.\n\n"
        "### Done when\n\n"
        "- You can explain the workflow in your own words.\n"
        "- You know where to find the source of truth next time.\n"
        "- You have a concrete next step or question for your mentor."
    )
    return _AILessonBody(body=body, summary=lesson_summary, infographic_source=None, infographic_kind=None)


def looks_like_placeholder_lesson(title: str | None, summary: str | None, body: str | None = None) -> bool:
    text = " ".join([title or "", summary or "", body or ""]).lower()
    return (
        "outline placeholder" in text
        or "add details with the mentor" in text
        or (title or "").strip().lower().startswith("lesson ")
    )


def ensure_lesson_body(lesson_title: str, lesson_summary: str, body: _AILessonBody, documents: list[Document]) -> _AILessonBody:
    if looks_like_placeholder_lesson(lesson_title, body.summary, body.body):
        return _fallback_lesson_body(lesson_title, lesson_summary, documents)
    return body


# ---------------------------------------------------------------------------
# AI: outline a new course
# ---------------------------------------------------------------------------

def ai_generate_course_outline(
    prompt_hint: str,
    documents: list[Document] | None = None,
    newcomer: NewcomerProfile | None = None,
    lesson_count: int = 4,
) -> _AICourseOutline:
    documents = documents or []
    system_prompt = _load("course_outline.txt")
    user_prompt = f"""
TOPIC HINT:
{prompt_hint}

{build_newcomer_context(newcomer) if newcomer else "(no newcomer profile provided)"}

LESSON COUNT REQUESTED: {lesson_count}

AVAILABLE DOCUMENTS:
{build_documents_context(documents)}
"""

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "course_outline",
                    "schema": _AICourseOutline.model_json_schema(),
                    "strict": True,
                }
            },
        )
        return _AICourseOutline.model_validate_json(response.output_text)
    except (ValidationError, json.JSONDecodeError, Exception):
        return _AICourseOutline(
            title=prompt_hint[:80] or "Onboarding course",
            summary=f"Short course about: {prompt_hint}",
            lessons=[
                _AILessonOutline(
                    title=f"Lesson {i + 1}",
                    summary="Outline placeholder — fill in with the mentor.",
                )
                for i in range(lesson_count)
            ],
        )


def ai_generate_lesson_body(
    course: Course,
    lesson_title: str,
    lesson_summary: str,
    documents: list[Document] | None = None,
) -> _AILessonBody:
    documents = documents or []
    system_prompt = _load("lesson_body.txt")
    user_prompt = f"""
COURSE TITLE: {course.title}
COURSE SUMMARY: {course.summary or "(none)"}

LESSON TITLE: {lesson_title}
LESSON SUMMARY: {lesson_summary}

AVAILABLE DOCUMENTS:
{build_documents_context(documents)}
"""

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "lesson_body",
                    "schema": _AILessonBody.model_json_schema(),
                    "strict": True,
                }
            },
        )
        return _AILessonBody.model_validate_json(response.output_text)
    except (ValidationError, json.JSONDecodeError, Exception):
        return _AILessonBody(
            body=f"## {lesson_title}\n\n{lesson_summary}\n\n_Add details with the mentor._",
            summary=lesson_summary,
            infographic_source=None,
            infographic_kind=None,
        )


# ---------------------------------------------------------------------------
# Orchestrator: create a course end-to-end with lessons
# ---------------------------------------------------------------------------

def create_ai_course(
    db: Session,
    prompt_hint: str,
    *,
    title: str | None = None,
    mentor_id: int | None = None,
    newcomer_id: int | None = None,
    plan_id: int | None = None,
    role_target: str | None = None,
    document_ids: list[int] | None = None,
    lesson_count: int = 4,
) -> Course:
    documents: list[Document] = []
    if document_ids:
        documents = (
            db.query(Document).filter(Document.id.in_(document_ids)).all()
        )

    newcomer = None
    if newcomer_id is not None:
        newcomer = (
            db.query(NewcomerProfile)
            .filter(NewcomerProfile.id == newcomer_id)
            .first()
        )

    outline = ai_generate_course_outline(
        prompt_hint=prompt_hint,
        documents=documents,
        newcomer=newcomer,
        lesson_count=lesson_count,
    )
    if not outline.lessons or any(looks_like_placeholder_lesson(ls.title, ls.summary) for ls in outline.lessons):
        outline.lessons = _fallback_lesson_outlines(prompt_hint, lesson_count)

    course = Course(
        title=title or outline.title,
        summary=outline.summary,
        plan_id=plan_id,
        newcomer_id=newcomer_id,
        mentor_id=mentor_id,
        role_target=role_target,
        status="draft",
        generated_by_ai=True,
        source_document_ids=document_ids or None,
    )
    db.add(course)
    db.flush()

    for i, ls in enumerate(outline.lessons):
        body = ai_generate_lesson_body(
            course=course,
            lesson_title=ls.title,
            lesson_summary=ls.summary,
            documents=documents,
        )
        body = ensure_lesson_body(ls.title, ls.summary, body, documents)
        lesson = Lesson(
            course_id=course.id,
            index=i + 1,
            title=ls.title,
            body=body.body,
            summary=body.summary,
            infographic_source=body.infographic_source,
            infographic_kind=body.infographic_kind or ("mermaid" if body.infographic_source else None),
            source_document_ids=document_ids or None,
        )
        db.add(lesson)

    db.commit()
    db.refresh(course)
    return course
