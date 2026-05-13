from datetime import date, datetime
from pydantic import BaseModel


class NewcomerDashboardProfile(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    job_title: str
    seniority: str
    team: str
    start_date: date | None
    onboarding_status: str
    mentor_id: int | None


class NewcomerDashboardPlan(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    generated_by_ai: bool
    mentor_approved: bool
    created_at: datetime


class NewcomerDashboardTask(BaseModel):
    id: int
    plan_id: int
    title: str
    description: str | None
    week_number: int | None
    day_number: int | None
    task_type: str
    status: str
    priority: str
    success_criteria: str | None


class NewcomerDashboardProgress(BaseModel):
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    todo_tasks: int
    progress_percent: int
    current_week: int
    current_day: int


class NewcomerDashboardQuestion(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime


class NewcomerDashboardSignal(BaseModel):
    id: int
    signal_type: str
    severity: str
    score: float
    title: str
    description: str
    suggested_action: str
    status: str
    created_at: datetime


class NewcomerDashboardResponse(BaseModel):
    newcomer: NewcomerDashboardProfile
    active_plan: NewcomerDashboardPlan | None
    progress: NewcomerDashboardProgress

    today_tasks: list[NewcomerDashboardTask]
    this_week_tasks: list[NewcomerDashboardTask]
    blocked_tasks: list[NewcomerDashboardTask]
    next_tasks: list[NewcomerDashboardTask]

    latest_questions: list[NewcomerDashboardQuestion]
    open_signals: list[NewcomerDashboardSignal]

    recommended_actions: list[str]