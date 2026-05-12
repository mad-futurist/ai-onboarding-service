from typing import Any

from sqlalchemy.orm import Session

from app.models.onboarding_event import OnboardingEvent


def log_onboarding_event(
    db: Session,
    newcomer_id: int,
    event_type: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    topic: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> OnboardingEvent:
    event = OnboardingEvent(
        newcomer_id=newcomer_id,
        user_id=user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        topic=topic,
        metadata_json=metadata_json,
    )

    db.add(event)
    db.flush()

    return event