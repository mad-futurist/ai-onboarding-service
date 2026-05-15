from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)

    plan_id = Column(
        Integer,
        ForeignKey("onboarding_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    index = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    start_day = Column(Integer, nullable=True)
    end_day = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    plan = relationship("OnboardingPlan", back_populates="sprints")

    weeks = relationship(
        "Week",
        back_populates="sprint",
        cascade="all, delete-orphan",
        order_by="Week.index",
    )
