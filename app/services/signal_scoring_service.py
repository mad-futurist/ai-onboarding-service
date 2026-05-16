from dataclasses import dataclass
from typing import Any


@dataclass
class SignalScoreResult:
    signal_type: str
    topic: str
    score: float
    confidence: float
    severity: str
    tone: str
    title: str
    description: str
    evidence_lines: list[str]
    suggested_action: str
    target_scope: str | None = None
    target_week_id: int | None = None
    target_task_id: int | None = None


def severity_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"

    if score >= 0.5:
        return "medium"

    return "low"


def clamp_score(score: float) -> float:
    return min(max(score, 0.0), 1.0)


def score_topic_friction(
    features: dict[str, Any],
    topic: str,
) -> SignalScoreResult | None:
    questions_count = features["questions_by_topic_count"].get(topic, 0)
    blocked_tasks_count = features["blocked_tasks_by_topic_count"].get(topic, 0)
    blocked_reports_count = features.get("blocked_reports_by_topic_count", {}).get(topic, 0)

    questions = features["questions_by_topic"].get(topic, [])

    repeated_sources = {
        source_title: count
        for source_title, count in features["repeated_sources_count"].items()
        if count >= 3
    }

    score = 0.0
    evidence_lines: list[str] = []

    if questions_count >= 2:
        score += 0.35
        evidence_lines.append(
            f"{questions_count} questions related to {topic} in the last {features['window_days']} days."
        )

    if questions_count >= 4:
        score += 0.15
        evidence_lines.append(
            f"The topic appears repeatedly, with {questions_count} total questions."
        )

    if blocked_tasks_count >= 1:
        score += 0.3
        evidence_lines.append(
            f"{blocked_tasks_count} blocked task(s) related to {topic}."
        )

    if blocked_reports_count >= 1:
        score += 0.35
        evidence_lines.append(
            f"{blocked_reports_count} blocker report(s) related to {topic}."
        )

    if repeated_sources:
        score += 0.2

        for source_title, count in repeated_sources.items():
            evidence_lines.append(
                f'Source "{source_title}" appeared in AI answers {count} times.'
            )

    score = clamp_score(score)

    if score < 0.5:
        return None

    for question in questions[:5]:
        evidence_lines.append(f'Question: "{question}"')

    severity = severity_from_score(score)

    tone = "critical" if blocked_tasks_count or blocked_reports_count or score >= 0.85 else "attention"
    signal_type = f"{topic}_friction"

    title_by_topic = {
        "deployment": "Possible deployment process confusion",
        "access": "Possible access or permissions blocker",
        "hr_process": "Possible HR process confusion",
        "code_review": "Possible code review workflow confusion",
        "testing": "Possible testing workflow friction",
        "architecture": "Possible architecture understanding gap",
        "jira_workflow": "Possible Jira workflow confusion",
    }

    action_by_topic = {
        "deployment": (
            "Schedule a 15-minute deployment walkthrough focused on staging, "
            "production release, rollback, and monitoring."
        ),
        "access": (
            "Check whether the newcomer has all required accounts, repository access, "
            "VPN access, and tool permissions."
        ),
        "hr_process": (
            "Send a short HR process summary and point the newcomer to the correct HR contact."
        ),
        "code_review": (
            "Explain the pull request workflow, review expectations, approval rules, and merge process."
        ),
        "testing": (
            "Provide a short testing guide and pair on one test/debugging example."
        ),
        "architecture": (
            "Schedule a codebase and architecture walkthrough with concrete service boundaries."
        ),
        "jira_workflow": (
            "Explain the team Jira workflow, ticket statuses, sprint rituals, and ownership rules."
        ),
    }

    return SignalScoreResult(
        signal_type=signal_type,
        topic=topic,
        score=score,
        confidence=score,
        severity=severity,
        tone=tone,
        title=title_by_topic.get(topic, f"Possible {topic} onboarding friction"),
        description=(
            f"The newcomer shows repeated friction around {topic}. "
            "This signal is based on onboarding events such as AI questions, blocked tasks, "
            "and repeated source usage."
        ),
        evidence_lines=evidence_lines,
        suggested_action=action_by_topic.get(
            topic,
            "Review this topic with the newcomer and decide whether to clarify documentation, assign a helper, or adapt the onboarding plan.",
        ),
    )


def score_all_signals(features: dict[str, Any]) -> list[SignalScoreResult]:
    topics = [
        "deployment",
        "access",
        "hr_process",
        "code_review",
        "testing",
        "architecture",
        "jira_workflow",
    ]

    results: list[SignalScoreResult] = []

    for topic in topics:
        result = score_topic_friction(
            features=features,
            topic=topic,
        )

        if result:
            results.append(result)

    return results
