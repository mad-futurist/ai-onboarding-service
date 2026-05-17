from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class TaskComment(Base):
    __tablename__ = "task_comments"

    id = Column(Integer, primary_key=True, index=True)

    task_id = Column(
        Integer,
        ForeignKey("onboarding_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    body = Column(Text, nullable=False)
    comment_type = Column(String(30), nullable=False, default="general")

    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("OnboardingTask", back_populates="comments")
