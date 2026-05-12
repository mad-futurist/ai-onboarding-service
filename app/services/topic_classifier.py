TOPIC_KEYWORDS = {
    "deployment": [
        "deploy",
        "deployment",
        "staging",
        "production",
        "release",
        "pipeline",
        "rollback",
    ],
    "access": [
        "access",
        "permission",
        "login",
        "account",
        "credentials",
        "vpn",
        "repository",
        "github",
        "gitlab",
    ],
    "hr_process": [
        "vacation",
        "holiday",
        "pointage",
        "time tracking",
        "sick leave",
        "hr",
        "absence",
    ],
    "code_review": [
        "pull request",
        "pr",
        "review",
        "approval",
        "merge",
        "code review",
    ],
    "testing": [
        "test",
        "pytest",
        "unit test",
        "integration test",
        "coverage",
        "ci",
    ],
    "architecture": [
        "architecture",
        "service",
        "database",
        "api gateway",
        "module",
        "backend",
        "flow",
    ],
    "jira_workflow": [
        "jira",
        "ticket",
        "sprint",
        "kanban",
        "backlog",
        "status",
    ],
}


def classify_topic(text: str | None) -> str:
    if not text:
        return "unknown"

    normalized = text.lower()

    topic_scores: dict[str, int] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            if keyword in normalized:
                score += 1

        if score > 0:
            topic_scores[topic] = score

    if not topic_scores:
        return "unknown"

    return max(topic_scores, key=topic_scores.get)