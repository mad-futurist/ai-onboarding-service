from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    related_task_id = Column(
        Integer,
        ForeignKey("onboarding_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_comment_id = Column(
        Integer,
        ForeignKey("task_comments.id", ondelete="SET NULL"),
        nullable=True,
    )

    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
