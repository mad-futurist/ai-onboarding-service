from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class AISignal(Base):
    __tablename__ = "ai_signals"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id"),
        nullable=False,
        index=True,
    )

    signal_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(50), nullable=False, default="medium")
    confidence = Column(Float, nullable=False, default=0.7)
    score = Column(Float, nullable=False, default=0.0)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    evidence = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=False)

    status = Column(String(50), nullable=False, default="open")

    occurrence_count = Column(Integer, nullable=False, default=1)

    target_scope = Column(String(20), nullable=True)
    target_week_id = Column(
        Integer,
        ForeignKey("weeks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_task_id = Column(
        Integer,
        ForeignKey("onboarding_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    newcomer = relationship("NewcomerProfile")