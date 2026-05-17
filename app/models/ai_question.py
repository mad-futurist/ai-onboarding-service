from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class AIQuestion(Base):
    __tablename__ = "ai_questions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=True, index=True)

    conversation_id = Column(
        Integer,
        ForeignKey("ai_conversations.id"),
        nullable=True,
        index=True,
    )

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    status = Column(String(50), nullable=False, default="answered")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship(
        "AIConversation",
        back_populates="questions",
    )

    sources = relationship(
        "AIQuestionSource",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class AIQuestionSource(Base):
    __tablename__ = "ai_question_sources"

    id = Column(Integer, primary_key=True, index=True)

    question_id = Column(Integer, ForeignKey("ai_questions.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    content_preview = Column(Text, nullable=False)

    similarity = Column(Float, nullable=False)

    question = relationship(
        "AIQuestion",
        back_populates="sources",
    )