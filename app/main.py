from fastapi import FastAPI

from app.core.config import settings
from app.api.routes import documents
from app.api.routes import users
from app.api.routes import newcomers
from app.api.routes import onboarding_plans
from app.api.routes import tasks


app = FastAPI(title=settings.APP_NAME)


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