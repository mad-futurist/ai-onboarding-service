from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import users
from app.api.routes import newcomers
from app.api.routes import documents
from app.api.routes import onboarding_plans
from app.api.routes import tasks
from app.api.routes import ai
from app.api.routes import ai_signals
from app.api.routes import onboarding_events
from app.api.routes import plan_adjustments
from app.api.routes import mentor_dashboard
from app.api.routes import newcomer_dashboard
from app.api.routes import blocked_reports
from app.api.routes import people
from app.api.routes import company_gaps
from app.api.routes import mentor_digests
from app.api.routes import mentor_actions
from app.api.routes import progress_snapshots
from app.api.routes import onboarding_reflections
from app.api.routes import newcomer_kb
from app.api.routes import user_story
from app.api.routes import knowledge
from app.api.routes import demo
from app.api.routes import courses
from app.api.routes import meetings
from app.api.routes import lesson_notes
from app.api.routes import assessments


app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }


app.include_router(users.router)
app.include_router(newcomers.router)
app.include_router(documents.router)
app.include_router(onboarding_plans.router)
app.include_router(tasks.router)
app.include_router(ai.router)
app.include_router(ai_signals.router)
app.include_router(onboarding_events.router)
app.include_router(plan_adjustments.router)
app.include_router(mentor_dashboard.router)
app.include_router(newcomer_dashboard.router)
app.include_router(blocked_reports.router)
app.include_router(people.router)
app.include_router(company_gaps.router)
app.include_router(mentor_digests.router)
app.include_router(mentor_actions.router)
app.include_router(progress_snapshots.router)
app.include_router(onboarding_reflections.router)
app.include_router(newcomer_kb.router)
app.include_router(user_story.router)
app.include_router(knowledge.router)
app.include_router(demo.router)
app.include_router(courses.router)
app.include_router(meetings.router)
app.include_router(lesson_notes.router)
app.include_router(assessments.router)
