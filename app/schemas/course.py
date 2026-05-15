from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


CourseStatus = Literal["draft", "pending_approval", "approved", "published", "rejected"]


class LessonCreate(BaseModel):
    index: int = 1
    title: str
    body: str | None = None
    summary: str | None = None
    infographic_url: str | None = None
    infographic_kind: str | None = None
    infographic_source: str | None = None
    video_url: str | None = None
    source_document_ids: list[int] | None = None


class LessonUpdate(BaseModel):
    index: int | None = None
    title: str | None = None
    body: str | None = None
    summary: str | None = None
    infographic_url: str | None = None
    infographic_kind: str | None = None
    infographic_source: str | None = None
    video_url: str | None = None
    source_document_ids: list[int] | None = None


class LessonRead(BaseModel):
    id: int
    course_id: int
    index: int
    title: str
    body: str | None
    summary: str | None
    infographic_url: str | None
    infographic_kind: str | None
    infographic_source: str | None
    video_url: str | None = None
    source_document_ids: list[int] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    title: str
    summary: str | None = None
    plan_id: int | None = None
    newcomer_id: int | None = None
    mentor_id: int | None = None
    role_target: str | None = None
    source_document_ids: list[int] | None = None


class CourseUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    plan_id: int | None = None
    newcomer_id: int | None = None
    mentor_id: int | None = None
    role_target: str | None = None
    source_document_ids: list[int] | None = None


class CourseAIGenerateRequest(BaseModel):
    title: str | None = None
    prompt_hint: str
    mentor_id: int | None = None
    newcomer_id: int | None = None
    plan_id: int | None = None
    role_target: str | None = None
    document_ids: list[int] = Field(default_factory=list)
    lesson_count: int = 4


class CourseRead(BaseModel):
    id: int
    plan_id: int | None
    newcomer_id: int | None
    mentor_id: int | None
    role_target: str | None
    title: str
    summary: str | None
    status: str
    generated_by_ai: bool
    source_document_ids: list[int] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approved_at: datetime | None = None
    published_at: datetime | None = None

    class Config:
        from_attributes = True


class CourseWithLessonsRead(CourseRead):
    lessons: list[LessonRead] = Field(default_factory=list)
