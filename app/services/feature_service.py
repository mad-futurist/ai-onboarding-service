from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.onboarding_event import OnboardingEvent


SIGNAL_TOPICS = [
    "deployment",
    "access",
    "hr_process",
    "code_review",
    "testing",
    "architecture",
    "jira_workflow",
]

TOPIC_ALIASES = {
    "access_issue": "access",
    "permissions": "access",
    "permission": "access",
    "blocked_access": "access",
    "hr": "hr_process",
    "vacation": "hr_process",
    "sick_leave": "hr_process",
    "pull_request": "code_review",
    "pr": "code_review",
    "ticket": "jira_workflow",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_events_for_newcomer(
    db: Session,
    newcomer_id: int,
    days: int = 7,
) -> list[OnboardingEvent]:
    since = utc_now() - timedelta(days=days)

    return (
        db.query(OnboardingEvent)
        .filter(OnboardingEvent.newcomer_id == newcomer_id)
        .filter(OnboardingEvent.created_at >= since)
        .order_by(OnboardingEvent.created_at.desc())
        .all()
    )


def safe_metadata(event: OnboardingEvent) -> dict[str, Any]:
    if isinstance(event.metadata_json, dict):
        return event.metadata_json

    return {}


def normalize_topic(topic: str | None) -> str:
    normalized = (topic or "unknown").strip().lower()
    return TOPIC_ALIASES.get(normalized, normalized)


def count_events_by_topic(
    events: list[OnboardingEvent],
    event_type: str | None = None,
) -> dict[str, int]:
    result: dict[str, int] = {}

    for event in events:
        if event_type and event.event_type != event_type:
            continue

        topic = normalize_topic(event.topic)
        result[topic] = result.get(topic, 0) + 1

    return result


def count_blocked_tasks_by_topic(events: list[OnboardingEvent]) -> dict[str, int]:
    result: dict[str, int] = {}

    for event in events:
        if event.event_type != "task_status_changed":
            continue

        metadata = safe_metadata(event)

        if metadata.get("new_status") != "blocked" and metadata.get("status") != "blocked":
            continue

        topic = normalize_topic(event.topic)
        result[topic] = result.get(topic, 0) + 1

    return result


def count_blocked_reports_by_topic(events: list[OnboardingEvent]) -> dict[str, int]:
    result: dict[str, int] = {}

    for event in events:
        if event.event_type != "blocked_reported":
            continue

        metadata = safe_metadata(event)
        topic = normalize_topic(event.topic or metadata.get("blocker_type"))
        result[topic] = result.get(topic, 0) + 1

    return result


def count_repeated_sources(events: list[OnboardingEvent]) -> dict[str, int]:
    source_counts: dict[str, int] = {}

    for event in events:
        if event.event_type != "ai_question_asked":
            continue

        metadata = safe_metadata(event)
        source_titles = metadata.get("source_titles") or []

        for title in source_titles:
            if not title:
                continue

            source_counts[title] = source_counts.get(title, 0) + 1

    return source_counts


def get_questions_by_topic(events: list[OnboardingEvent]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}

    for event in events:
        if event.event_type != "ai_question_asked":
            continue

        metadata = safe_metadata(event)
        question = metadata.get("question")

        if not question:
            continue

        topic = normalize_topic(event.topic)

        if topic not in result:
            result[topic] = []

        result[topic].append(question)

    return result


def compute_newcomer_features(
    db: Session,
    newcomer_id: int,
    days: int = 7,
) -> dict[str, Any]:
    events = get_events_for_newcomer(
        db=db,
        newcomer_id=newcomer_id,
        days=days,
    )

    questions_by_topic_count = count_events_by_topic(
        events=events,
        event_type="ai_question_asked",
    )

    blocked_tasks_by_topic_count = count_blocked_tasks_by_topic(events)
    blocked_reports_by_topic_count = count_blocked_reports_by_topic(events)
    repeated_sources_count = count_repeated_sources(events)
    questions_by_topic = get_questions_by_topic(events)

    total_questions = sum(questions_by_topic_count.values())
    total_blocked_tasks = sum(blocked_tasks_by_topic_count.values())
    total_blocked_reports = sum(blocked_reports_by_topic_count.values())

    dominant_topic = "unknown"

    if questions_by_topic_count:
        dominant_topic = max(
            questions_by_topic_count,
            key=questions_by_topic_count.get,
        )

    return {
        "newcomer_id": newcomer_id,
        "window_days": days,
        "events_count": len(events),
        "total_questions": total_questions,
        "total_blocked_tasks": total_blocked_tasks,
        "total_blocked_reports": total_blocked_reports,
        "dominant_topic": dominant_topic,
        "questions_by_topic_count": questions_by_topic_count,
        "blocked_tasks_by_topic_count": blocked_tasks_by_topic_count,
        "blocked_reports_by_topic_count": blocked_reports_by_topic_count,
        "repeated_sources_count": repeated_sources_count,
        "questions_by_topic": questions_by_topic,
    }
