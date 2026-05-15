from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.ai_question import AIQuestion
from app.models.ai_signal import AISignal
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.services.feature_service import compute_newcomer_features
from app.services.signal_scoring_service import score_all_signals
from app.services.signal_upsert_service import upsert_signal


DEPLOYMENT_KEYWORDS = [
    "deploy",
    "deployment",
    "staging",
    "production",
    "release",
    "pipeline",
    "rollback",
]

HR_KEYWORDS = [
    "vacation",
    "holiday",
    "pointage",
    "time tracking",
    "sick leave",
    "hr",
]

ACCESS_KEYWORDS = [
    "access",
    "permission",
    "login",
    "account",
    "credentials",
    "vpn",
]


def normalize_text(value: str | None) -> str:
    return (value or "").lower().strip()


def question_contains_any(question: str, keywords: list[str]) -> bool:
    normalized = normalize_text(question)
    return any(keyword in normalized for keyword in keywords)


def open_signal_exists(
    db: Session,
    newcomer_id: int,
    signal_type: str,
) -> bool:
    existing = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id)
        .filter(AISignal.signal_type == signal_type)
        .filter(AISignal.status == "open")
        .first()
    )

    return existing is not None


def get_newcomer_questions(
    db: Session,
    newcomer_id: int,
) -> list[AIQuestion]:
    return (
        db.query(AIQuestion)
        .options(joinedload(AIQuestion.sources))
        .filter(AIQuestion.newcomer_id == newcomer_id)
        .order_by(AIQuestion.id.desc())
        .all()
    )


def get_newcomer_tasks(
    db: Session,
    newcomer_id: int,
) -> list[OnboardingTask]:
    plans = (
        db.query(OnboardingPlan)
        .filter(OnboardingPlan.newcomer_id == newcomer_id)
        .all()
    )

    plan_ids = [plan.id for plan in plans]

    if not plan_ids:
        return []

    return (
        db.query(OnboardingTask)
        .filter(OnboardingTask.plan_id.in_(plan_ids))
        .all()
    )


def create_signal(
    db: Session,
    newcomer_id: int,
    signal_type: str,
    severity: str,
    confidence: float,
    title: str,
    description: str,
    evidence: str,
    suggested_action: str,
) -> AISignal:
    signal = AISignal(
        newcomer_id=newcomer_id,
        signal_type=signal_type,
        severity=severity,
        confidence=confidence,
        title=title,
        description=description,
        evidence=evidence,
        suggested_action=suggested_action,
        status="open",
    )

    db.add(signal)
    db.flush()

    return signal


def detect_deployment_confusion(
    db: Session,
    newcomer_id: int,
    questions: list[AIQuestion],
    tasks: list[OnboardingTask],
) -> AISignal | None:
    if open_signal_exists(db, newcomer_id, "deployment_confusion"):
        return None

    deployment_questions = [
        question
        for question in questions
        if question_contains_any(question.question, DEPLOYMENT_KEYWORDS)
    ]

    deployment_tasks = [
        task
        for task in tasks
        if question_contains_any(
            f"{task.title} {task.description} {task.task_type}",
            DEPLOYMENT_KEYWORDS,
        )
    ]

    blocked_or_open_deployment_tasks = [
        task
        for task in deployment_tasks
        if task.status in ["todo", "in_progress", "blocked"]
    ]

    if len(deployment_questions) < 2:
        return None

    severity = "medium"

    if len(deployment_questions) >= 3 or blocked_or_open_deployment_tasks:
        severity = "high"

    evidence_lines = [
        f"- {len(deployment_questions)} questions related to deployment/release/staging.",
    ]

    for question in deployment_questions[:5]:
        evidence_lines.append(f'- Question: "{question.question}"')

    if blocked_or_open_deployment_tasks:
        evidence_lines.append(
            f"- {len(blocked_or_open_deployment_tasks)} deployment-related tasks are still open or blocked."
        )

        for task in blocked_or_open_deployment_tasks[:5]:
            evidence_lines.append(
                f'- Task: "{task.title}" with status "{task.status}"'
            )

    used_sources = []

    for question in deployment_questions:
        for source in question.sources:
            used_sources.append(source.title)

    unique_sources = sorted(set(used_sources))

    if unique_sources:
        evidence_lines.append(
            "- Sources repeatedly involved: " + ", ".join(unique_sources[:5])
        )

    confidence = 0.78

    if len(deployment_questions) >= 3:
        confidence = 0.85

    return create_signal(
        db=db,
        newcomer_id=newcomer_id,
        signal_type="deployment_confusion",
        severity=severity,
        confidence=confidence,
        title="Possible deployment process confusion",
        description=(
            "The newcomer asked several questions related to deployment, staging, "
            "production release, or pipeline flow. This may indicate friction before "
            "their first production-ready contribution."
        ),
        evidence="\n".join(evidence_lines),
        suggested_action=(
            "Schedule a 15-minute deployment walkthrough with the mentor or DevOps owner. "
            "Focus on staging pipeline, release approval, rollback, and post-deploy monitoring."
        ),
    )


def detect_hr_friction(
    db: Session,
    newcomer_id: int,
    questions: list[AIQuestion],
) -> AISignal | None:
    if open_signal_exists(db, newcomer_id, "hr_friction"):
        return None

    hr_questions = [
        question
        for question in questions
        if question_contains_any(question.question, HR_KEYWORDS)
    ]

    if len(hr_questions) < 2:
        return None

    evidence_lines = [
        f"- {len(hr_questions)} questions related to HR processes.",
    ]

    for question in hr_questions[:5]:
        evidence_lines.append(f'- Question: "{question.question}"')

    return create_signal(
        db=db,
        newcomer_id=newcomer_id,
        signal_type="hr_friction",
        severity="medium",
        confidence=0.72,
        title="Possible HR process confusion",
        description=(
            "The newcomer asked several questions about HR processes such as vacation, "
            "time tracking, sick leave, or administrative workflows."
        ),
        evidence="\n".join(evidence_lines),
        suggested_action=(
            "Send the newcomer a short HR process summary and point them to the correct HR contact."
        ),
    )


def detect_access_friction(
    db: Session,
    newcomer_id: int,
    questions: list[AIQuestion],
) -> AISignal | None:
    if open_signal_exists(db, newcomer_id, "access_friction"):
        return None

    access_questions = [
        question
        for question in questions
        if question_contains_any(question.question, ACCESS_KEYWORDS)
    ]

    if len(access_questions) < 2:
        return None

    evidence_lines = [
        f"- {len(access_questions)} questions related to access, accounts, permissions, or login.",
    ]

    for question in access_questions[:5]:
        evidence_lines.append(f'- Question: "{question.question}"')

    return create_signal(
        db=db,
        newcomer_id=newcomer_id,
        signal_type="access_friction",
        severity="high",
        confidence=0.8,
        title="Possible access or permissions blocker",
        description=(
            "The newcomer asked repeated questions about access, accounts, permissions, "
            "credentials, or login. This can block onboarding progress."
        ),
        evidence="\n".join(evidence_lines),
        suggested_action=(
            "Check whether the newcomer has all required accounts, permissions, repository access, "
            "VPN access, and tool invitations."
        ),
    )


def detect_blocked_tasks(
    db: Session,
    newcomer_id: int,
    tasks: list[OnboardingTask],
) -> AISignal | None:
    if open_signal_exists(db, newcomer_id, "blocked_task"):
        return None

    blocked_tasks = [task for task in tasks if task.status == "blocked"]

    if not blocked_tasks:
        return None

    evidence_lines = [
        f"- {len(blocked_tasks)} onboarding tasks are currently blocked.",
    ]

    for task in blocked_tasks[:5]:
        evidence_lines.append(f'- Task: "{task.title}"')

    return create_signal(
        db=db,
        newcomer_id=newcomer_id,
        signal_type="blocked_task",
        severity="high",
        confidence=0.9,
        title="Blocked onboarding task detected",
        description=(
            "One or more onboarding tasks are marked as blocked. "
            "This requires mentor attention because the newcomer may not be able to progress independently."
        ),
        evidence="\n".join(evidence_lines),
        suggested_action=(
            "Review the blocked tasks with the newcomer and decide whether to clarify instructions, "
            "assign a helper, or adapt the onboarding plan."
        ),
    )


def detect_repeated_source_friction(
    db: Session,
    newcomer_id: int,
    questions: list[AIQuestion],
) -> AISignal | None:
    if open_signal_exists(db, newcomer_id, "knowledge_friction"):
        return None

    source_counts: dict[str, int] = {}

    for question in questions:
        for source in question.sources:
            source_counts[source.title] = source_counts.get(source.title, 0) + 1

    repeated_sources = {
        title: count
        for title, count in source_counts.items()
        if count >= 3
    }

    if not repeated_sources:
        return None

    evidence_lines = ["- Same source appears repeatedly in AI answers."]

    for title, count in repeated_sources.items():
        evidence_lines.append(f'- Source: "{title}" used {count} times.')

    return create_signal(
        db=db,
        newcomer_id=newcomer_id,
        signal_type="knowledge_friction",
        severity="medium",
        confidence=0.76,
        title="Possible knowledge friction",
        description=(
            "The same documentation source appears repeatedly in the newcomer questions. "
            "This may mean the topic is important, unclear, or not actionable enough."
        ),
        evidence="\n".join(evidence_lines),
        suggested_action=(
            "Review the repeatedly used document and consider creating a shorter role-specific guide "
            "or scheduling a focused explanation."
        ),
    )


def detect_fast_completion_signals(
    db: Session,
    newcomer_id: int,
    tasks: list[OnboardingTask],
) -> list[AISignal]:
    """Fire a positive signal when a task moved to done quickly (proxy: ≤ 24h)."""
    created: list[AISignal] = []

    for task in tasks:
        if task.status != "done":
            continue
        if not task.created_at or not task.updated_at:
            continue

        delta = task.updated_at - task.created_at
        if delta.total_seconds() > 24 * 3600:
            continue

        already = (
            db.query(AISignal)
            .filter(AISignal.newcomer_id == newcomer_id)
            .filter(AISignal.signal_type == "fast_completion")
            .filter(AISignal.target_task_id == task.id)
            .first()
        )
        if already:
            continue

        signal = AISignal(
            newcomer_id=newcomer_id,
            signal_type="fast_completion",
            severity="low",
            tone="positive",
            confidence=0.82,
            score=0.6,
            title=f'Fast win: "{task.title}" completed quickly',
            description=(
                "Task moved to done within the first day with no blockers. "
                "This is a positive signal — the newcomer is moving fast on this scope."
            ),
            evidence=(
                f'- Task: "{task.title}" (status: done)\n'
                f"- Created: {task.created_at.isoformat()}\n"
                f"- Updated: {task.updated_at.isoformat()}\n"
                f"- Elapsed: {int(delta.total_seconds() // 3600)}h"
            ),
            suggested_action=(
                "Consider proposing a stretch task or pulling the next milestone forward."
            ),
            status="open",
            occurrence_count=1,
            target_scope="task",
            target_task_id=task.id,
            target_week_id=task.week_id,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(signal)
        db.flush()
        created.append(signal)

    return created


def detect_deployment_heavy_plan(
    db: Session,
    newcomer_id: int,
    tasks: list[OnboardingTask],
) -> AISignal | None:
    """≥3 deployment-related tasks in the plan → suggest consolidating."""
    deploy_tasks = [
        task
        for task in tasks
        if question_contains_any(
            f"{task.title or ''} {task.description or ''} {task.task_type or ''}",
            DEPLOYMENT_KEYWORDS,
        )
    ]

    if len(deploy_tasks) < 3:
        return None

    plan_id = deploy_tasks[0].plan_id

    already = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id)
        .filter(AISignal.signal_type == "deployment_heavy_plan")
        .filter(AISignal.status == "open")
        .first()
    )
    if already:
        return None

    evidence_lines = [
        f"- {len(deploy_tasks)} deployment-related tasks queued in the plan.",
    ]
    for task in deploy_tasks[:5]:
        evidence_lines.append(f'- Task: "{task.title}" (type: {task.task_type})')

    signal = AISignal(
        newcomer_id=newcomer_id,
        signal_type="deployment_heavy_plan",
        severity="medium",
        tone="attention",
        confidence=0.8,
        score=0.55,
        title="Plan looks deployment-heavy",
        description=(
            "The plan contains several deployment-focused tasks. "
            "Consider consolidating to keep the onboarding ramp balanced."
        ),
        evidence="\n".join(evidence_lines),
        suggested_action=(
            f"Review the {len(deploy_tasks)} deployment tasks and consider merging "
            "two of them into a single end-to-end exercise, freeing time for product context."
        ),
        status="open",
        occurrence_count=1,
        target_scope="plan",
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(signal)
    db.flush()
    return signal


def detect_signals_for_newcomer(
    db: Session,
    newcomer_id: int,
) -> tuple[list[AISignal], int, int]:
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )

    if not newcomer:
        raise ValueError("Newcomer not found")

    features = compute_newcomer_features(
        db=db,
        newcomer_id=newcomer_id,
        days=7,
    )

    score_results = score_all_signals(features)

    signals: list[AISignal] = []
    created_count = 0
    updated_count = 0

    for score_result in score_results:
        signal, created = upsert_signal(
            db=db,
            newcomer_id=newcomer_id,
            score_result=score_result,
        )

        signals.append(signal)

        if created:
            created_count += 1
        else:
            updated_count += 1

    # Positive / plan-shape detectors that the scoring pipeline doesn't cover.
    tasks = get_newcomer_tasks(db=db, newcomer_id=newcomer_id)

    for positive in detect_fast_completion_signals(db, newcomer_id, tasks):
        signals.append(positive)
        created_count += 1

    deploy_heavy = detect_deployment_heavy_plan(db, newcomer_id, tasks)
    if deploy_heavy is not None:
        signals.append(deploy_heavy)
        created_count += 1

    db.commit()

    for signal in signals:
        db.refresh(signal)

    return signals, created_count, updated_count


def resolve_signal(
    db: Session,
    signal_id: int,
) -> AISignal | None:
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()

    if not signal:
        return None

    signal.status = "resolved"
    signal.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(signal)

    return signal


def ignore_signal(
    db: Session,
    signal_id: int,
) -> AISignal | None:
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()

    if not signal:
        return None

    signal.status = "ignored"
    signal.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(signal)

    return signal