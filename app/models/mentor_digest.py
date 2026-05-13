from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, JSON, func

from app.db.base import Base


class MentorDigest(Base):
    __tablename__ = "mentor_digests"

    id = Column(Integer, primary_key=True, index=True)

    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)

    summary = Column(Text, nullable=False)
    highlights = Column(JSON, nullable=True)
    risks = Column(JSON, nullable=True)
    recommended_actions = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
