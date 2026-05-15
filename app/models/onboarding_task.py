from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id = Column(Integer, primary_key=True, index=True)

    plan_id = Column(Integer, ForeignKey("onboarding_plans.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    week_number = Column(Integer, nullable=True)
    day_number = Column(Integer, nullable=True)

    week_id = Column(
        Integer,
        ForeignKey("weeks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sprint_id = Column(
        Integer,
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    task_type = Column(String(100), nullable=False, default="general")
    status = Column(String(50), nullable=False, default="todo")
    priority = Column(String(50), nullable=False, default="medium")

    success_criteria = Column(Text, nullable=True)

    acceptance_criteria = Column(Text, nullable=True)
    examples = Column(JSON, nullable=True)
    links = Column(JSON, nullable=True)
    manually_edited_fields = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    plan = relationship(
        "OnboardingPlan",
        back_populates="tasks",
    )

    week = relationship("Week", back_populates="tasks")
