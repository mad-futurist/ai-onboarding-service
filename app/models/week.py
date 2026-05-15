from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Week(Base):
    __tablename__ = "weeks"

    id = Column(Integer, primary_key=True, index=True)

    plan_id = Column(
        Integer,
        ForeignKey("onboarding_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sprint_id = Column(
        Integer,
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    index = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    goals = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    plan = relationship("OnboardingPlan", back_populates="weeks")
    sprint = relationship("Sprint", back_populates="weeks")

    tasks = relationship(
        "OnboardingTask",
        back_populates="week",
        order_by="OnboardingTask.day_number",
    )
