from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func

from app.db.base import Base


class AIAnswerFeedback(Base):
    __tablename__ = "ai_answer_feedbacks"

    id = Column(Integer, primary_key=True, index=True)

    question_id = Column(Integer, ForeignKey("ai_questions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=True, index=True)

    rating = Column(Integer, nullable=True)
    feedback_type = Column(String(100), nullable=False)
    comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
