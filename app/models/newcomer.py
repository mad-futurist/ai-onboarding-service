from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class NewcomerProfile(Base):
    __tablename__ = "newcomer_profiles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    job_title = Column(String(255), nullable=False)
    seniority = Column(String(50), nullable=False)
    team = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=True)

    onboarding_status = Column(String(50), default="not_started", nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User",
        back_populates="newcomer_profile",
        foreign_keys=[user_id],
    )

    mentor = relationship(
        "User",
        back_populates="mentored_newcomers",
        foreign_keys=[mentor_id],
    )

    onboarding_plans = relationship(
        "OnboardingPlan",
        back_populates="newcomer",
        cascade="all, delete-orphan",
    )

    arena_sessions = relationship(
        "ArenaSession",
        back_populates="newcomer",
        cascade="all, delete-orphan",
    )
