from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.models.company_onboarding_gap import CompanyOnboardingGap

SIGNAL_TO_GAP: dict[str, dict] = {
    "deployment_confusion": {
        "gap_type": "process_gap",
        "topic": "deployment",
        "title": "Deployment process unclear for newcomers",
        "description": "Multiple newcomers have shown confusion around deployment, staging pipelines, or release flow.",
        "suggested_fix": "Create a concise deployment guide tailored for first-timers and schedule a walkthrough session.",
    },
    "hr_friction": {
        "gap_type": "documentation_gap",
        "topic": "hr_process",
        "title": "HR processes documentation insufficient",
        "description": "Multiple newcomers repeatedly ask about HR processes such as vacation, time tracking, or sick leave.",
        "suggested_fix": "Update the HR handbook with a quick-reference FAQ for common new-hire questions.",
    },
    "access_friction": {
        "gap_type": "process_gap",
        "topic": "access_management",
        "title": "Access provisioning causing onboarding delays",
        "description": "Multiple newcomers face issues obtaining necessary system access, permissions, or credentials.",
        "suggested_fix": "Create an access checklist and assign an IT onboarding buddy for the first week.",
    },
    "knowledge_friction": {
        "gap_type": "documentation_gap",
        "topic": "knowledge_base",
        "title": "Knowledge base documents not actionable enough",
        "description": "Newcomers repeatedly consult the same documents without finding clear answers.",
        "suggested_fix": "Rewrite the most-referenced documents with step-by-step instructions and role-specific examples.",
    },
    "blocked_task": {
        "gap_type": "process_gap",
        "topic": "task_clarity",
        "title": "Onboarding tasks lack sufficient guidance",
        "description": "Multiple newcomers get blocked on tasks without enough context or support.",
        "suggested_fix": "Add success criteria, related resources, and people to contact to each onboarding task.",
    },
}

MIN_NEWCOMERS = 2


def detect_company_gaps(db: Session) -> tuple[list[CompanyOnboardingGap], int, int]:
    rows = (
        db.query(AISignal.signal_type, func.count(AISignal.newcomer_id.distinct()).label("cnt"))
        .filter(AISignal.status == "open")
        .group_by(AISignal.signal_type)
        .all()
    )

    created_count = 0
    updated_count = 0
    result_gaps: list[CompanyOnboardingGap] = []

    for signal_type, newcomer_count in rows:
        if newcomer_count < MIN_NEWCOMERS:
            continue

        meta = SIGNAL_TO_GAP.get(signal_type)
        if not meta:
            continue

        existing = (
            db.query(CompanyOnboardingGap)
            .filter(CompanyOnboardingGap.gap_type == meta["gap_type"])
            .filter(CompanyOnboardingGap.topic == meta["topic"])
            .first()
        )

        evidence = f"{newcomer_count} newcomers currently have open '{signal_type}' signals."

        if existing:
            existing.affected_newcomers_count = newcomer_count
            existing.evidence = evidence
            db.flush()
            updated_count += 1
            result_gaps.append(existing)
        else:
            gap = CompanyOnboardingGap(
                gap_type=meta["gap_type"],
                topic=meta["topic"],
                title=meta["title"],
                description=meta["description"],
                evidence=evidence,
                affected_newcomers_count=newcomer_count,
                suggested_fix=meta.get("suggested_fix"),
                status="open",
            )
            db.add(gap)
            db.flush()
            created_count += 1
            result_gaps.append(gap)

    db.commit()
    for gap in result_gaps:
        db.refresh(gap)

    return result_gaps, created_count, updated_count
