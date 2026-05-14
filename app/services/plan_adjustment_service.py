from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.plan_adjustment import PlanAdjustmentSuggestion


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_latest_plan_for_newcomer(
    db: Session,
    newcomer_id: int,
) -> OnboardingPlan | None:
    return (
        db.query(OnboardingPlan)
        .filter(OnboardingPlan.newcomer_id == newcomer_id)
        .order_by(OnboardingPlan.id.desc())
        .first()
    )


def build_changes_for_signal(signal: AISignal) -> list[dict]:
    signal_type = signal.signal_type

    if signal_type in ["deployment_friction", "deployment_confusion"]:
        return [
            {
                "action": "add_task",
                "title": "Deployment walkthrough with DevOps or mentor",
                "description": (
                    "Review staging pipeline, production release approval, rollback process, "
                    "and post-deploy monitoring."
                ),
                "week_number": 2,
                "day_number": 4,
                "task_type": "meet_person",
                "priority": "high",
                "success_criteria": (
                    "The newcomer can explain the deployment flow from staging to production."
                ),
            },
            {
                "action": "add_task",
                "title": "Staging deployment simulation",
                "description": (
                    "Run a safe staging deployment simulation with mentor support."
                ),
                "week_number": 3,
                "day_number": 1,
                "task_type": "technical_practice",
                "priority": "high",
                "success_criteria": (
                    "The newcomer can complete the staging deployment checklist confidently."
                ),
            },
            {
                "action": "add_task",
                "title": "Deployment confidence checkpoint",
                "description": (
                    "Short mentor checkpoint to validate what is clear and what remains risky."
                ),
                "week_number": 3,
                "day_number": 3,
                "task_type": "checkpoint",
                "priority": "medium",
                "success_criteria": (
                    "The mentor confirms whether the newcomer is ready for a production-related task."
                ),
            },
        ]

    if signal_type in ["access_friction"]:
        return [
            {
                "action": "add_task",
                "title": "Access and permissions checklist",
                "description": (
                    "Verify repository access, VPN, internal tools, CI/CD dashboard, "
                    "documentation spaces, and required team channels."
                ),
                "week_number": 1,
                "day_number": 1,
                "task_type": "setup",
                "priority": "high",
                "success_criteria": (
                    "The newcomer confirms access to all required tools without blockers."
                ),
            }
        ]

    if signal_type in ["hr_process_friction", "hr_friction"]:
        return [
            {
                "action": "add_task",
                "title": "HR basics clarification",
                "description": (
                    "Review vacation request, time tracking, sick leave, and HR contact process."
                ),
                "week_number": 1,
                "day_number": 5,
                "task_type": "hr_process",
                "priority": "medium",
                "success_criteria": (
                    "The newcomer knows where to handle standard HR workflows."
                ),
            }
        ]

    if signal_type in ["code_review_friction"]:
        return [
            {
                "action": "add_task",
                "title": "Code review workflow walkthrough",
                "description": (
                    "Explain PR creation, reviewers, approval rules, merge criteria, and expected feedback cycle."
                ),
                "week_number": 2,
                "day_number": 2,
                "task_type": "technical_practice",
                "priority": "high",
                "success_criteria": (
                    "The newcomer can open a PR that follows the team review workflow."
                ),
            }
        ]

    if signal_type in ["testing_friction"]:
        return [
            {
                "action": "add_task",
                "title": "Testing workflow pairing session",
                "description": (
                    "Pair on one unit test and one integration test for the current codebase."
                ),
                "week_number": 2,
                "day_number": 3,
                "task_type": "technical_practice",
                "priority": "medium",
                "success_criteria": (
                    "The newcomer can run tests locally and add a simple test confidently."
                ),
            }
        ]

    return [
        {
            "action": "add_task",
            "title": "Mentor clarification checkpoint",
            "description": (
                "Review the detected onboarding friction and clarify the next best step."
            ),
            "week_number": 2,
            "day_number": 5,
            "task_type": "checkpoint",
            "priority": "medium",
            "success_criteria": (
                "The newcomer and mentor agree on what should be clarified or adapted."
            ),
        }
    ]


def generate_adjustment_from_signal(
    db: Session,
    signal_id: int,
) -> PlanAdjustmentSuggestion:
    signal = db.query(AISignal).filter(AISignal.id == signal_id).first()

    if not signal:
        raise ValueError("AI signal not found")

    if signal.status != "open":
        raise ValueError("Only open signals can generate plan adjustments")

    plan = get_latest_plan_for_newcomer(
        db=db,
        newcomer_id=signal.newcomer_id,
    )

    if not plan:
        raise ValueError("Onboarding plan not found")

    existing_pending = (
        db.query(PlanAdjustmentSuggestion)
        .filter(PlanAdjustmentSuggestion.signal_id == signal.id)
        .filter(PlanAdjustmentSuggestion.status == "pending")
        .first()
    )

    if existing_pending:
        return existing_pending

    changes = build_changes_for_signal(signal)

    adjustment = PlanAdjustmentSuggestion(
        newcomer_id=signal.newcomer_id,
        plan_id=plan.id,
        signal_id=signal.id,
        title=f"Plan adjustment for: {signal.title}",
        reason=(
            f"This suggestion was generated because of the AI signal '{signal.title}'.\n\n"
            f"Evidence:\n{signal.evidence}"
        ),
        suggested_changes=changes,
        status="pending",
    )

    db.add(adjustment)
    db.commit()
    db.refresh(adjustment)

    return adjustment


def approve_adjustment(
    db: Session,
    adjustment_id: int,
) -> PlanAdjustmentSuggestion | None:
    adjustment = (
        db.query(PlanAdjustmentSuggestion)
        .filter(PlanAdjustmentSuggestion.id == adjustment_id)
        .first()
    )

    if not adjustment:
        return None

    adjustment.status = "approved"
    adjustment.reviewed_at = utc_now()

    db.commit()
    db.refresh(adjustment)

    return adjustment


def reject_adjustment(
    db: Session,
    adjustment_id: int,
) -> PlanAdjustmentSuggestion | None:
    adjustment = (
        db.query(PlanAdjustmentSuggestion)
        .filter(PlanAdjustmentSuggestion.id == adjustment_id)
        .first()
    )

    if not adjustment:
        return None

    adjustment.status = "rejected"
    adjustment.reviewed_at = utc_now()

    db.commit()
    db.refresh(adjustment)

    return adjustment


def apply_adjustment(
    db: Session,
    adjustment_id: int,
) -> PlanAdjustmentSuggestion | None:
    adjustment = (
        db.query(PlanAdjustmentSuggestion)
        .filter(PlanAdjustmentSuggestion.id == adjustment_id)
        .first()
    )

    if not adjustment:
        return None

    if adjustment.status != "approved":
        raise ValueError("Only approved adjustments can be applied")

    changes = adjustment.suggested_changes or []

    for change in changes:
        if change.get("action") not in ["add_task", "add"]:
            continue

        task = OnboardingTask(
            plan_id=adjustment.plan_id,
            title=change.get("title"),
            description=change.get("description"),
            week_number=change.get("week_number"),
            day_number=change.get("day_number"),
            task_type=change.get("task_type") or "general",
            priority=change.get("priority") or "medium",
            success_criteria=change.get("success_criteria"),
            status="todo",
        )

        db.add(task)

    adjustment.status = "applied"
    adjustment.applied_at = utc_now()

    db.commit()
    db.refresh(adjustment)

    return adjustment
