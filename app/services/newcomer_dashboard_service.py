from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models.ai_question import AIQuestion
from app.models.ai_signal import AISignal
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask


WORKING_DAYS_PER_WEEK = 5


def get_current_onboarding_day(start_date: date | None) -> int:
    if not start_date:
        return 1

    today = date.today()
    delta = (today - start_date).days + 1

    if delta < 1:
        return 1

    return delta


def get_current_week_and_day(start_date: date | None) -> tuple[int, int]:
    onboarding_day = get_current_onboarding_day(start_date)

    current_week = ((onboarding_day - 1) // WORKING_DAYS_PER_WEEK) + 1
    current_day = ((onboarding_day - 1) % WORKING_DAYS_PER_WEEK) + 1

    return current_week, current_day


def get_latest_plan(
    db: Session,
    newcomer_id: int,
) -> OnboardingPlan | None:
    return (
        db.query(OnboardingPlan)
        .filter(OnboardingPlan.newcomer_id == newcomer_id)
        .order_by(OnboardingPlan.id.desc())
        .first()
    )


def get_plan_tasks(
    db: Session,
    plan_id: int | None,
) -> list[OnboardingTask]:
    if not plan_id:
        return []

    return (
        db.query(OnboardingTask)
        .filter(OnboardingTask.plan_id == plan_id)
        .order_by(
            OnboardingTask.week_number.asc().nulls_last(),
            OnboardingTask.day_number.asc().nulls_last(),
            OnboardingTask.id.asc(),
        )
        .all()
    )


def compute_progress(
    tasks: list[OnboardingTask],
    current_week: int,
    current_day: int,
) -> dict:
    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.status == "done"])
    in_progress_tasks = len([task for task in tasks if task.status == "in_progress"])
    in_review_tasks = len([task for task in tasks if task.status == "in_review"])
    blocked_tasks = len([task for task in tasks if task.status == "blocked"])
    todo_tasks = len([task for task in tasks if task.status == "todo"])

    progress_percent = 0

    if total_tasks > 0:
        progress_percent = round((completed_tasks / total_tasks) * 100)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "in_review_tasks": in_review_tasks,
        "blocked_tasks": blocked_tasks,
        "todo_tasks": todo_tasks,
        "progress_percent": progress_percent,
        "current_week": current_week,
        "current_day": current_day,
    }


def get_today_tasks(
    tasks: list[OnboardingTask],
    current_week: int,
    current_day: int,
) -> list[OnboardingTask]:
    today_tasks = [
        task
        for task in tasks
        if task.week_number == current_week
        and task.day_number == current_day
        and task.status != "done"
    ]

    if today_tasks:
        return today_tasks

    return [
        task
        for task in tasks
        if task.status in ["todo", "in_progress", "blocked"]
    ][:3]


def get_this_week_tasks(
    tasks: list[OnboardingTask],
    current_week: int,
) -> list[OnboardingTask]:
    return [
        task
        for task in tasks
        if task.week_number == current_week
    ]


def get_blocked_tasks(tasks: list[OnboardingTask]) -> list[OnboardingTask]:
    return [
        task
        for task in tasks
        if task.status == "blocked"
    ]


def get_next_tasks(tasks: list[OnboardingTask]) -> list[OnboardingTask]:
    return [
        task
        for task in tasks
        if task.status in ["todo", "in_progress"]
    ][:5]


def get_latest_questions(
    db: Session,
    newcomer_id: int,
    limit: int = 5,
) -> list[AIQuestion]:
    return (
        db.query(AIQuestion)
        .filter(AIQuestion.newcomer_id == newcomer_id)
        .order_by(AIQuestion.id.desc())
        .limit(limit)
        .all()
    )


def get_open_signals(
    db: Session,
    newcomer_id: int,
    limit: int = 3,
) -> list[AISignal]:
    return (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id)
        .filter(AISignal.status == "open")
        .order_by(AISignal.score.desc(), AISignal.id.desc())
        .limit(limit)
        .all()
    )


def build_recommended_actions(
    progress: dict,
    today_tasks: list[OnboardingTask],
    blocked_tasks: list[OnboardingTask],
    open_signals: list[AISignal],
) -> list[str]:
    actions: list[str] = []

    if blocked_tasks:
        actions.append("Review your blocked tasks and ask AI or your mentor for help.")

    if open_signals:
        top_signal = open_signals[0]
        actions.append(top_signal.suggested_action)

    if today_tasks:
        actions.append("Continue your current onboarding tasks for today.")

    if progress["progress_percent"] == 0:
        actions.append("Start with your first onboarding task to begin tracking progress.")

    if progress["progress_percent"] >= 80:
        actions.append("You are close to completing this onboarding phase. Prepare questions for your next mentor checkpoint.")

    if not actions:
        actions.append("Open your onboarding plan and continue with the next recommended task.")

    return actions[:4]


def serialize_task(task: OnboardingTask) -> dict:
    return {
        "id": task.id,
        "plan_id": task.plan_id,
        "title": task.title,
        "description": task.description,
        "week_number": task.week_number,
        "day_number": task.day_number,
        "task_type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "success_criteria": task.success_criteria,
    }


def serialize_question(question: AIQuestion) -> dict:
    return {
        "id": question.id,
        "question": question.question,
        "answer": question.answer,
        "created_at": question.created_at,
    }


def serialize_signal(signal: AISignal) -> dict:
    return {
        "id": signal.id,
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "score": signal.score,
        "title": signal.title,
        "description": signal.description,
        "suggested_action": signal.suggested_action,
        "status": signal.status,
        "created_at": signal.created_at,
    }


def get_newcomer_dashboard(
    db: Session,
    newcomer_id: int,
) -> dict | None:
    newcomer = (
        db.query(NewcomerProfile)
        .options(joinedload(NewcomerProfile.user))
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )

    if not newcomer:
        return None

    current_week, current_day = get_current_week_and_day(
        newcomer.start_date,
    )

    active_plan = get_latest_plan(
        db=db,
        newcomer_id=newcomer.id,
    )

    plan_id = active_plan.id if active_plan else None

    tasks = get_plan_tasks(
        db=db,
        plan_id=plan_id,
    )

    progress = compute_progress(
        tasks=tasks,
        current_week=current_week,
        current_day=current_day,
    )

    today_tasks = get_today_tasks(
        tasks=tasks,
        current_week=current_week,
        current_day=current_day,
    )

    this_week_tasks = get_this_week_tasks(
        tasks=tasks,
        current_week=current_week,
    )

    blocked_tasks = get_blocked_tasks(tasks)
    next_tasks = get_next_tasks(tasks)

    latest_questions = get_latest_questions(
        db=db,
        newcomer_id=newcomer.id,
    )

    open_signals = get_open_signals(
        db=db,
        newcomer_id=newcomer.id,
    )

    recommended_actions = build_recommended_actions(
        progress=progress,
        today_tasks=today_tasks,
        blocked_tasks=blocked_tasks,
        open_signals=open_signals,
    )

    active_plan_payload = None

    if active_plan:
        active_plan_payload = {
            "id": active_plan.id,
            "title": active_plan.title,
            "description": active_plan.description,
            "status": active_plan.status,
            "generated_by_ai": active_plan.generated_by_ai,
            "mentor_approved": active_plan.mentor_approved,
            "created_at": active_plan.created_at,
        }

    return {
        "newcomer": {
            "id": newcomer.id,
            "user_id": newcomer.user_id,
            "full_name": newcomer.user.full_name if newcomer.user else "Unknown",
            "email": newcomer.user.email if newcomer.user else "unknown@example.com",
            "job_title": newcomer.job_title,
            "seniority": newcomer.seniority,
            "team": newcomer.team,
            "start_date": newcomer.start_date,
            "onboarding_status": newcomer.onboarding_status,
            "mentor_id": newcomer.mentor_id,
        },
        "active_plan": active_plan_payload,
        "progress": progress,
        "today_tasks": [serialize_task(task) for task in today_tasks],
        "this_week_tasks": [serialize_task(task) for task in this_week_tasks],
        "blocked_tasks": [serialize_task(task) for task in blocked_tasks],
        "next_tasks": [serialize_task(task) for task in next_tasks],
        "latest_questions": [
            serialize_question(question)
            for question in latest_questions
        ],
        "open_signals": [
            serialize_signal(signal)
            for signal in open_signals
        ],
        "recommended_actions": recommended_actions,
    }
