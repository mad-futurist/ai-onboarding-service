from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func

from app.db.base import Base


class ScheduledMeeting(Base):
    __tablename__ = "scheduled_meetings"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organizer_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    plan_id = Column(
        Integer,
        ForeignKey("onboarding_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id = Column(
        Integer,
        ForeignKey("onboarding_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    signal_id = Column(
        Integer,
        ForeignKey("ai_signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(255), nullable=False)
    agenda = Column(Text, nullable=True)

    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)

    teams_join_url = Column(String(1024), nullable=True)
    attendee_emails = Column(JSON, nullable=True)

    status = Column(String(50), nullable=False, default="proposed")  # proposed | confirmed | cancelled

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
