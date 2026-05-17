from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload

from app.models.ai_signal import AISignal
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.task_comment import TaskComment


KANBAN_STATUSES = ["in_progress", "in_review", "blocked"]

PRIORITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}
SEVERITY_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _days_in_status(task: OnboardingTask) -> int:
    if not task.updated_at:
        return 0
    now = datetime.now(timezone.utc)
    updated = task.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    delta = now - updated
    return max(delta.days, 0)


def _urgency_score(
    task: OnboardingTask,
    signal: AISignal | None,
    days_in_status: int,
) -> float:
    priority = PRIORITY_WEIGHTS.get((task.priority or "medium").lower(), 2)
    severity = (
        SEVERITY_WEIGHTS.get((signal.severity or "low").lower(), 0)
        if signal
        else 0
    )
    return priority * 2 + severity * 3 + min(days_in_status, 14)


def _build_task_card(
    db: Session,
    task: OnboardingTask,
    newcomer: NewcomerProfile,
    signal: AISignal | None,
) -> dict:
    last_comment = (
        db.query(TaskComment)
        .filter(TaskComment.task_id == task.id)
        .order_by(TaskComment.created_at.desc())
        .first()
    )
    return_count = (
        db.query(TaskComment)
        .filter(
            TaskComment.task_id == task.id,
            TaskComment.comment_type == "review_return",
        )
        .count()
    )
    days_in_status = _days_in_status(task)
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "task_type": task.task_type,
        "plan_id": task.plan_id,
        "week_number": task.week_number,
        "day_number": task.day_number,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "days_in_status": days_in_status,
        "review_return_count": return_count,
        "urgency_score": round(
            _urgency_score(task, signal, days_in_status), 2
        ),
        "newcomer": {
            "id": newcomer.id,
            "full_name": newcomer.user.full_name if newcomer.user else "Unknown",
            "user_id": newcomer.user_id,
            "job_title": newcomer.job_title,
            "team": newcomer.team,
        },
        "latest_signal": (
            {
                "id": signal.id,
                "signal_type": signal.signal_type,
                "severity": signal.severity,
                "tone": signal.tone,
                "title": signal.title,
            }
            if signal
            else None
        ),
        "last_comment": (
            {
                "id": last_comment.id,
                "body": last_comment.body,
                "comment_type": last_comment.comment_type,
                "from_status": last_comment.from_status,
                "to_status": last_comment.to_status,
                "created_at": last_comment.created_at.isoformat()
                if last_comment.created_at
                else None,
            }
            if last_comment
            else None
        ),
    }


def get_mentor_kanban(
    db: Session,
    *,
    mentor_id: int | None,
    statuses: list[str] | None = None,
    newcomer_id: int | None = None,
    priority: str | None = None,
    task_type: str | None = None,
    has_open_signal: bool | None = None,
    search: str | None = None,
) -> dict:
    effective_statuses = statuses or KANBAN_STATUSES
    effective_statuses = [s for s in effective_statuses if s in KANBAN_STATUSES]
    if not effective_statuses:
        effective_statuses = KANBAN_STATUSES

    newcomer_query = db.query(NewcomerProfile).options(
        joinedload(NewcomerProfile.user)
    )
    if mentor_id is not None:
        newcomer_query = newcomer_query.filter(
            NewcomerProfile.mentor_id == mentor_id
        )
    if newcomer_id is not None:
        newcomer_query = newcomer_query.filter(
            NewcomerProfile.id == newcomer_id
        )

    newcomers = newcomer_query.all()
    newcomer_by_id = {n.id: n for n in newcomers}

    if not newcomer_by_id:
        return {
            "columns": {status: [] for status in effective_statuses},
            "filters": {
                "newcomers": [],
                "priorities": ["low", "medium", "high"],
                "task_types": [],
            },
        }

    plan_query = (
        db.query(OnboardingPlan)
        .filter(OnboardingPlan.newcomer_id.in_(newcomer_by_id.keys()))
    )
    plans = plan_query.all()
    plan_by_id = {p.id: p for p in plans}
    if not plan_by_id:
        return {
            "columns": {status: [] for status in effective_statuses},
            "filters": {
                "newcomers": [
                    {
                        "id": n.id,
                        "full_name": n.user.full_name if n.user else "Unknown",
                    }
                    for n in newcomers
                ],
                "priorities": ["low", "medium", "high"],
                "task_types": [],
            },
        }

    task_query = db.query(OnboardingTask).filter(
        OnboardingTask.plan_id.in_(plan_by_id.keys()),
        OnboardingTask.status.in_(effective_statuses),
    )
    if priority:
        task_query = task_query.filter(OnboardingTask.priority == priority)
    if task_type:
        task_query = task_query.filter(OnboardingTask.task_type == task_type)
    if search:
        task_query = task_query.filter(
            OnboardingTask.title.ilike(f"%{search}%")
        )

    tasks = task_query.all()

    open_signals = (
        db.query(AISignal)
        .filter(
            AISignal.status == "open",
            AISignal.target_task_id.in_([t.id for t in tasks]),
        )
        .order_by(AISignal.score.desc(), AISignal.id.desc())
        .all()
    )
    signal_by_task: dict[int, AISignal] = {}
    for s in open_signals:
        signal_by_task.setdefault(s.target_task_id, s)

    columns: dict[str, list[dict]] = {s: [] for s in effective_statuses}
    task_types_seen: set[str] = set()

    for task in tasks:
        plan = plan_by_id.get(task.plan_id)
        if not plan:
            continue
        newcomer = newcomer_by_id.get(plan.newcomer_id)
        if not newcomer:
            continue
        signal = signal_by_task.get(task.id)
        if has_open_signal is True and signal is None:
            continue
        if has_open_signal is False and signal is not None:
            continue

        card = _build_task_card(db, task, newcomer, signal)
        columns.setdefault(task.status, []).append(card)
        if task.task_type:
            task_types_seen.add(task.task_type)

    for status in columns:
        columns[status].sort(key=lambda c: c["urgency_score"], reverse=True)

    return {
        "columns": columns,
        "filters": {
            "newcomers": [
                {
                    "id": n.id,
                    "full_name": n.user.full_name if n.user else "Unknown",
                }
                for n in newcomers
            ],
            "priorities": ["low", "medium", "high"],
            "task_types": sorted(task_types_seen),
        },
    }
