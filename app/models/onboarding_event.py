from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func

from app.db.base import Base


class OnboardingEvent(Base):
    __tablename__ = "onboarding_events"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    event_type = Column(String(100), nullable=False, index=True)

    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)

    topic = Column(String(100), nullable=True, index=True)

    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)