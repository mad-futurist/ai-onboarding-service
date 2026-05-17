from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=True, index=True)

    title = Column(String(255), nullable=False, default="New conversation")

    # Polymorphic context: lets us scope a thread to a document or a task without an FK,
    # so we can later add new context types without schema changes.
    context_type = Column(String(20), nullable=True)
    context_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    questions = relationship(
        "AIQuestion",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AIQuestion.id.asc()",
    )

    __table_args__ = (
        Index("ix_ai_conversations_context", "context_type", "context_id"),
    )
