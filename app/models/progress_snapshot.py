from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func

from app.db.base import Base


class ProgressSnapshot(Base):
    __tablename__ = "progress_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=False, index=True)

    week_number = Column(Integer, nullable=False)
    completed_tasks = Column(Integer, nullable=False, default=0)
    blocked_tasks = Column(Integer, nullable=False, default=0)
    open_signals = Column(Integer, nullable=False, default=0)
    progress_percent = Column(Integer, nullable=False, default=0)

    strengths = Column(JSON, nullable=True)
    gaps = Column(JSON, nullable=True)
    mentor_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
