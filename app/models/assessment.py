from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=True, index=True)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    status = Column(String(50), default="draft", nullable=False)

    mentor_notes = Column(Text, nullable=True)
    role_context = Column(Text, nullable=True)
    source_document_ids = Column(JSON, nullable=True)

    generated_by_ai = Column(Boolean, default=False, nullable=False)
    used_fallback = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)

    questions = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.order_index",
    )

    submissions = relationship(
        "AssessmentSubmission",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)

    order_index = Column(Integer, nullable=False, default=0)
    question_type = Column(String(50), nullable=False)

    prompt = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)
    expected_answer = Column(Text, nullable=True)
    skill_tag = Column(String(100), nullable=True)
    difficulty = Column(String(50), nullable=True, default="medium")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assessment = relationship("Assessment", back_populates="questions")
    answers = relationship(
        "AssessmentAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class AssessmentSubmission(Base):
    __tablename__ = "assessment_submissions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=False, index=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    overall_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)

    assessment = relationship("Assessment", back_populates="submissions")
    answers = relationship(
        "AssessmentAnswer",
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("assessment_submissions.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("assessment_questions.id"), nullable=False, index=True)

    answer_text = Column(Text, nullable=True)
    selected_option_ids = Column(JSON, nullable=True)

    ai_score = Column(Float, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    mentor_score = Column(Float, nullable=True)
    mentor_feedback = Column(Text, nullable=True)

    submission = relationship("AssessmentSubmission", back_populates="answers")
    question = relationship("AssessmentQuestion", back_populates="answers")
