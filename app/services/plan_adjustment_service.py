from datetime import datetime, timedelta, timezone

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


def _task_summary(task: OnboardingTask) -> str:
    return f"{task.title} ({task.status}, {task.priority}, week {task.week_number or '?'})"


def _unfinished_tasks(tasks: list[OnboardingTask]) -> list[OnboardingTask]:
    return [task for task in tasks if task.status != "done"]


def _topic_matches_task(signal: AISignal, task: OnboardingTask) -> bool:
    topic = (signal.signal_type or "").replace("_friction", "")
    text = f"{task.title or ''} {task.description or ''} {task.task_type or ''}".lower()
    if topic in {"deployment", "access", "testing", "architecture"}:
        return topic in text
    if topic == "code_review":
        return any(word in text for word in ["review", "pr", "pull request", "merge"])
    if topic == "jira_workflow":
        return any(word in text for word in ["jira", "ticket", "sprint", "backlog"])
    if topic == "hr_process":
        return any(word in text for word in ["hr", "vacation", "leave", "pointage"])
    return False


def _unique_changes(changes: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique: list[dict] = []
    for change in changes:
        key = (
            change.get("action"),
            change.get("task_id"),
            change.get("title"),
            change.get("field"),
            change.get("value"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(change)
    return unique


def _build_period_changes(
    tasks: list[OnboardingTask],
    signals: list[AISignal],
) -> list[dict]:
    changes: list[dict] = []
    unfinished = _unfinished_tasks(tasks)
    critical_signals = [s for s in signals if (s.tone or "") == "critical" or s.severity == "high"]
    attention_signals = [s for s in signals if (s.tone or "") == "attention" and s.severity != "high"]
    positive_signals = [s for s in signals if (s.tone or "") == "positive"]

    for signal in critical_signals:
        target_task = next((t for t in unfinished if t.id == signal.target_task_id), None)
        if target_task:
            changes.append(
                {
                    "action": "replace_task",
                    "task_id": target_task.id,
                    "title": target_task.title,
                    "description": (
                        f"{target_task.description or target_task.title}\n\n"
                        f"Adjustment from signal: {signal.suggested_action}"
                    ),
                    "week_number": target_task.week_number,
                    "day_number": target_task.day_number,
                    "task_type": target_task.task_type,
                    "priority": "high",
                    "success_criteria": (
                        target_task.success_criteria
                        or "The newcomer can continue this task without an active blocker."
                    ),
                    "reason": f"Critical signal: {signal.title}",
                }
            )
        else:
            changes.extend(build_changes_for_signal(signal)[:1])

    for signal in attention_signals:
        matching = [task for task in unfinished if _topic_matches_task(signal, task)]
        for task in matching[:2]:
            changes.append(
                {
                    "action": "update_task_field",
                    "task_id": task.id,
                    "field": "description",
                    "value": (
                        f"{task.description or task.title}\n\n"
                        f"Mentor focus: {signal.suggested_action}"
                    ),
                    "title": f"Clarify {task.title}",
                    "description": f"Adds signal-aware guidance to {_task_summary(task)}.",
                    "reason": f"Attention signal: {signal.title}",
                }
            )
        if not matching:
            changes.extend(build_changes_for_signal(signal)[:1])

    if any(s.signal_type == "plan_stall" for s in signals) and unfinished:
        first = unfinished[0]
        changes.append(
            {
                "action": "replace_task",
                "task_id": first.id,
                "title": f"Starter slice: {first.title}",
                "description": (
                    "Shrink this into a first concrete action the newcomer can finish today. "
                    f"Original scope: {first.description or first.title}"
                ),
                "week_number": first.week_number,
                "day_number": first.day_number,
                "task_type": first.task_type,
                "priority": "high",
                "success_criteria": "One visible first step is completed and reviewed with the mentor.",
                "reason": "Plan stall risk: make the first unfinished task smaller.",
            }
        )

    deployment_tasks = [
        task
        for task in unfinished
        if any(
            word in f"{task.title} {task.description or ''} {task.task_type}".lower()
            for word in ["deploy", "deployment", "staging", "release"]
        )
    ]
    if any(s.signal_type == "deployment_heavy_plan" for s in signals) and len(deployment_tasks) > 2:
        protected_task_ids = {
            change.get("task_id")
            for change in changes
            if change.get("action") in {"replace_task", "update_task_field"}
        }
        removable_deployment_tasks = [
            task for task in deployment_tasks[2:] if task.id not in protected_task_ids
        ]
        for task in removable_deployment_tasks[:2]:
            changes.append(
                {
                    "action": "delete_task",
                    "task_id": task.id,
                    "title": task.title,
                    "description": "Remove or defer this duplicate deployment task from the current period.",
                    "reason": "Deployment-heavy plan: keep the current period focused on one end-to-end deployment exercise.",
                }
            )

    if critical_signals and unfinished:
        changes.append(
            {
                "action": "adjust_remaining_period",
                "title": "Rebalance unfinished tasks around blockers",
                "description": "Move unfinished work into a blocker-first order and keep only actionable tasks in the current period.",
                "task_ids": [task.id for task in unfinished],
                "priority": "high",
                "reason": f"{len(critical_signals)} critical signal(s) should steer the rest of the period.",
            }
        )

    if positive_signals and not critical_signals:
        changes.append(
            {
                "action": "add_task",
                "title": "Stretch task: own the next small improvement",
                "description": "Give the newcomer one optional end-to-end task that builds on their current momentum.",
                "week_number": max([task.week_number or 1 for task in tasks] or [1]),
                "day_number": None,
                "task_type": "stretch",
                "priority": "medium",
                "success_criteria": "The newcomer ships or presents a small improvement with minimal mentor help.",
                "reason": "Good signals show readiness for slightly more autonomy.",
            }
        )

    if len(critical_signals) >= 2 or len(changes) >= 5:
        changes.append(
            {
                "action": "add_period",
                "title": "Recovery and confidence period",
                "description": "Create a short follow-up period to absorb deferred work after blockers are cleared.",
                "period_label": "Recovery sprint",
                "goal": "Clear blockers, rebuild confidence, and resume the original ramp without overload.",
                "reason": "Multiple signals indicate the current period may be overloaded.",
            }
        )

    return _unique_changes(changes)


def generate_adjustment_for_period(
    db: Session,
    plan_id: int,
) -> PlanAdjustmentSuggestion:
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == plan_id).first()
    if not plan:
        raise ValueError("Onboarding plan not found")

    tasks = (
        db.query(OnboardingTask)
        .filter(OnboardingTask.plan_id == plan.id)
        .order_by(OnboardingTask.week_number.asc(), OnboardingTask.day_number.asc(), OnboardingTask.id.asc())
        .all()
    )
    signals = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == plan.newcomer_id)
        .filter(AISignal.status == "open")
        .order_by(AISignal.id.desc())
        .all()
    )
    if not signals:
        raise ValueError("No open signals found for this newcomer")

    existing_pending = (
        db.query(PlanAdjustmentSuggestion)
        .filter(PlanAdjustmentSuggestion.plan_id == plan.id)
        .filter(PlanAdjustmentSuggestion.signal_id.is_(None))
        .filter(PlanAdjustmentSuggestion.status == "pending")
        .order_by(PlanAdjustmentSuggestion.id.desc())
        .first()
    )
    changes = _build_period_changes(tasks=tasks, signals=signals)
    if not changes:
        raise ValueError("Signals found, but no actionable adjustment could be drafted")

    signal_lines = [
        f"- {signal.title} ({signal.signal_type}, {signal.severity}, tone={signal.tone})"
        for signal in signals
    ]
    unfinished = _unfinished_tasks(tasks)
    title = f"Signal-based adjustment draft for {plan.period_label or plan.title}"
    reason = (
        "This draft uses all currently open signals for the newcomer and only changes "
        "tasks that are not already done.\n\n"
        f"Open signals considered:\n{chr(10).join(signal_lines)}\n\n"
        f"Unfinished tasks in this period:\n{chr(10).join('- ' + _task_summary(t) for t in unfinished) or '- none'}"
    )

    if existing_pending:
        existing_pending.title = title
        existing_pending.reason = reason
        existing_pending.suggested_changes = changes
        existing_pending.target_scope = "plan"
        db.commit()
        db.refresh(existing_pending)
        return existing_pending

    adjustment = PlanAdjustmentSuggestion(
        newcomer_id=plan.newcomer_id,
        plan_id=plan.id,
        signal_id=None,
        title=title,
        reason=reason,
        suggested_changes=changes,
        status="pending",
        target_scope="plan",
    )
    db.add(adjustment)
    db.commit()
    db.refresh(adjustment)
    return adjustment


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
        target_scope=signal.target_scope,
        target_week_id=signal.target_week_id,
        target_task_id=signal.target_task_id,
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
        action = change.get("action")

        if action in ("add_task", "add"):
            task = OnboardingTask(
                plan_id=adjustment.plan_id,
                title=change.get("title"),
                description=change.get("description"),
                week_number=change.get("week_number"),
                day_number=change.get("day_number"),
                week_id=adjustment.target_week_id if adjustment.target_scope == "week" else change.get("week_id"),
                task_type=change.get("task_type") or "general",
                priority=change.get("priority") or "medium",
                success_criteria=change.get("success_criteria"),
                acceptance_criteria=change.get("acceptance_criteria"),
                status="todo",
            )
            db.add(task)
            continue

        if action == "update_task_field":
            task_id = change.get("task_id") or adjustment.target_task_id
            target_task = (
                db.query(OnboardingTask)
                .filter(OnboardingTask.id == task_id)
                .first()
            )
            if target_task and target_task.status != "done":
                field = change.get("field")
                value = change.get("value")
                if field in {
                    "title",
                    "description",
                    "success_criteria",
                    "acceptance_criteria",
                    "task_type",
                    "priority",
                    "examples",
                    "links",
                }:
                    setattr(target_task, field, value)
            continue

        if action == "replace_task":
            task_id = change.get("task_id") or adjustment.target_task_id
            target_task = (
                db.query(OnboardingTask)
                .filter(OnboardingTask.id == task_id)
                .first()
            )
            if target_task and target_task.status != "done":
                for field in (
                    "title",
                    "description",
                    "week_number",
                    "day_number",
                    "task_type",
                    "priority",
                    "success_criteria",
                    "acceptance_criteria",
                ):
                    if field in change:
                        setattr(target_task, field, change[field])
            continue

        if action == "delete_task":
            task_id = change.get("task_id")
            target_task = (
                db.query(OnboardingTask)
                .filter(OnboardingTask.id == task_id)
                .filter(OnboardingTask.plan_id == adjustment.plan_id)
                .first()
            )
            if target_task and target_task.status != "done":
                db.delete(target_task)
            continue

        if action == "adjust_remaining_period":
            task_ids = change.get("task_ids") or []
            remaining = (
                db.query(OnboardingTask)
                .filter(OnboardingTask.plan_id == adjustment.plan_id)
                .filter(OnboardingTask.id.in_(task_ids))
                .all()
            )
            for idx, task in enumerate([task for task in remaining if task.status != "done"], start=1):
                task.priority = change.get("priority") or task.priority
                task.day_number = idx
            continue

        if action == "add_period":
            current_plan = (
                db.query(OnboardingPlan)
                .filter(OnboardingPlan.id == adjustment.plan_id)
                .first()
            )
            if not current_plan:
                continue

            next_start = current_plan.period_end + timedelta(days=1) if current_plan.period_end else None
            next_end = next_start + timedelta(days=14) if next_start else None
            new_plan = OnboardingPlan(
                newcomer_id=current_plan.newcomer_id,
                mentor_id=current_plan.mentor_id,
                title=change.get("title") or "Follow-up onboarding period",
                description=change.get("description"),
                period_label=change.get("period_label") or change.get("title") or "Follow-up period",
                period_start=next_start,
                period_end=next_end,
                goal=change.get("goal"),
                status="draft",
                generated_by_ai=True,
                mentor_approved=False,
            )
            db.add(new_plan)
            db.flush()
            db.add(
                OnboardingTask(
                    plan_id=new_plan.id,
                    title="Re-check blockers and restart the ramp",
                    description="Review what was cleared, what is still unclear, and pick the next autonomous task.",
                    week_number=1,
                    day_number=1,
                    task_type="checkpoint",
                    priority="high",
                    success_criteria="The newcomer and mentor agree on the next unblocked milestone.",
                    status="todo",
                )
            )
            continue

        # Unknown action: skip silently (forward-compatible).

    adjustment.status = "applied"
    adjustment.applied_at = utc_now()

    db.commit()
    db.refresh(adjustment)

    return adjustment
