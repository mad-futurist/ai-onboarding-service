from datetime import date, datetime
from pydantic import BaseModel


class MentorDashboardSignalItem(BaseModel):
    id: int
    signal_type: str
    severity: str
    score: float
    title: str
    status: str
    created_at: datetime


class MentorDashboardAdjustmentItem(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime


class MentorDashboardNewcomerItem(BaseModel):
    newcomer_id: int
    full_name: str
    job_title: str
    seniority: str
    team: str
    start_date: date | None
    onboarding_status: str

    active_plan_id: int | None
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    progress_percent: int

    computed_status: str
    latest_signal: MentorDashboardSignalItem | None


class MentorDashboardResponse(BaseModel):
    active_newcomers: int
    on_track_count: int
    needs_attention_count: int
    blocked_count: int
    newcomers: list[MentorDashboardNewcomerItem]


class NewcomerDashboardDetail(BaseModel):
    newcomer: MentorDashboardNewcomerItem
    signals: list[MentorDashboardSignalItem]
    adjustments: list[MentorDashboardAdjustmentItem]