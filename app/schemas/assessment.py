from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


QuestionType = Literal["mcq", "short_answer", "scenario"]
Difficulty = Literal["easy", "medium", "hard"]
AssessmentStatus = Literal["draft", "published", "submitted", "evaluated"]


# ---------- Options (for MCQ) ----------

class AssessmentOption(BaseModel):
    id: str
    label: str
    is_correct: bool = False


# ---------- Question schemas ----------

class AssessmentQuestionBase(BaseModel):
    question_type: QuestionType
    prompt: str
    context: str | None = None
    options: list[AssessmentOption] | None = None
    expected_answer: str | None = None
    skill_tag: str | None = None
    difficulty: Difficulty | None = "medium"


class AssessmentQuestionCreate(AssessmentQuestionBase):
    order_index: int | None = None


class AssessmentQuestionUpdate(BaseModel):
    question_type: QuestionType | None = None
    prompt: str | None = None
    context: str | None = None
    options: list[AssessmentOption] | None = None
    expected_answer: str | None = None
    skill_tag: str | None = None
    difficulty: Difficulty | None = None
    order_index: int | None = None


class AssessmentQuestionRead(AssessmentQuestionBase):
    id: int
    assessment_id: int
    order_index: int

    class Config:
        from_attributes = True


# ---------- Assessment schemas ----------

class AssessmentRead(BaseModel):
    id: int
    newcomer_id: int | None
    mentor_id: int | None
    title: str
    status: AssessmentStatus
    mentor_notes: str | None
    role_context: str | None
    source_document_ids: list[int] | None = None
    generated_by_ai: bool
    used_fallback: bool
    created_at: datetime
    published_at: datetime | None
    questions: list[AssessmentQuestionRead] = []

    class Config:
        from_attributes = True


class AssessmentUpdate(BaseModel):
    title: str | None = None
    mentor_notes: str | None = None
    role_context: str | None = None


# ---------- Generation requests ----------

class AssessmentGenerateRequest(BaseModel):
    newcomer_id: int | None = None
    mentor_id: int | None = None
    mentor_notes: str | None = None
    role_context: str | None = None
    document_ids: list[int] = Field(default_factory=list)
    question_count: int = Field(default=8, ge=1, le=30)
    question_types: list[QuestionType] = Field(
        default_factory=lambda: ["mcq", "short_answer", "scenario"]
    )
    job_title: str | None = None
    seniority: str | None = None
    team: str | None = None
    known_skills: str | None = None
    known_gaps: str | None = None


class AssessmentRegenerateRequest(BaseModel):
    scope: Literal["all", "question"]
    target_id: int | None = None
    mentor_notes: str | None = None
    document_ids: list[int] = Field(default_factory=list)


# ---------- AI output schemas (LLM structured response) ----------

class AIAssessmentOptionOutput(BaseModel):
    id: str
    label: str
    is_correct: bool


class AIAssessmentQuestionOutput(BaseModel):
    question_type: QuestionType
    prompt: str
    context: str | None = None
    options: list[AIAssessmentOptionOutput] | None = None
    expected_answer: str | None = None
    skill_tag: str | None = None
    difficulty: Difficulty


class AIAssessmentOutput(BaseModel):
    title: str
    questions: list[AIAssessmentQuestionOutput]


class AIAssessmentServiceResult(BaseModel):
    output: AIAssessmentOutput
    used_fallback: bool = False


# ---------- Submission schemas ----------

class AnswerSubmissionItem(BaseModel):
    question_id: int
    answer_text: str | None = None
    selected_option_ids: list[str] | None = None


class AssessmentSubmissionCreate(BaseModel):
    newcomer_id: int
    duration_seconds: int | None = None
    answers: list[AnswerSubmissionItem]


class AssessmentAnswerRead(BaseModel):
    id: int
    question_id: int
    answer_text: str | None
    selected_option_ids: list[str] | None
    ai_score: float | None
    ai_feedback: str | None
    mentor_score: float | None
    mentor_feedback: str | None

    class Config:
        from_attributes = True


class AssessmentSubmissionRead(BaseModel):
    id: int
    assessment_id: int
    newcomer_id: int
    started_at: datetime | None
    submitted_at: datetime | None
    duration_seconds: int | None
    overall_score: float | None
    summary: str | None
    answers: list[AssessmentAnswerRead] = []

    class Config:
        from_attributes = True


class AssessmentAnswerUpdate(BaseModel):
    mentor_score: float | None = None
    mentor_feedback: str | None = None


# ---------- Publish ----------

class AssessmentPublishRequest(BaseModel):
    newcomer_id: int


# ---------- AI evaluation schemas ----------

class AIAnswerEvaluationOutput(BaseModel):
    score: float
    feedback: str


class AIEvaluationOutput(BaseModel):
    overall_score: float
    summary: str
    answers: list[dict]
