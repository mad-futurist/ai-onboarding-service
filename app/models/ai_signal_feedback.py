from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func

from app.db.base import Base


class AISignalFeedback(Base):
    __tablename__ = "ai_signal_feedbacks"

    id = Column(Integer, primary_key=True, index=True)

    signal_id = Column(Integer, ForeignKey("ai_signals.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    feedback_type = Column(String(100), nullable=False)
    comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
