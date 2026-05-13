from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func

from app.db.base import Base


class PlanAdjustmentSuggestion(Base):
    __tablename__ = "plan_adjustment_suggestions"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id"),
        nullable=False,
        index=True,
    )

    plan_id = Column(
        Integer,
        ForeignKey("onboarding_plans.id"),
        nullable=False,
        index=True,
    )

    signal_id = Column(
        Integer,
        ForeignKey("ai_signals.id"),
        nullable=True,
        index=True,
    )

    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)

    suggested_changes = Column(JSON, nullable=False)

    status = Column(String(50), nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)