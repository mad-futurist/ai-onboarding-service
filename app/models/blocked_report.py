from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.db.base import Base


class BlockedReport(Base):
    __tablename__ = "blocked_reports"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("onboarding_tasks.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    blocker_type = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ai_suggestion = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default="open")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
