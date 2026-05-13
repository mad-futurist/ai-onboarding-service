from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func

from app.db.base import Base


class OnboardingReflection(Base):
    __tablename__ = "onboarding_reflections"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=False, index=True)

    what_became_clear = Column(Text, nullable=True)
    what_was_confusing = Column(Text, nullable=True)
    most_helpful_document = Column(String(255), nullable=True)
    most_helpful_person = Column(String(255), nullable=True)
    improvement_suggestions = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
