from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class OnboardingPlan(Base):
    __tablename__ = "onboarding_plans"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(50), default="draft", nullable=False)

    generated_by_ai = Column(Boolean, default=False, nullable=False)
    mentor_approved = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    newcomer = relationship(
        "NewcomerProfile",
        back_populates="onboarding_plans",
    )

    tasks = relationship(
        "OnboardingTask",
        back_populates="plan",
        cascade="all, delete-orphan",
    )