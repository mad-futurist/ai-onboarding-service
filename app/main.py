from fastapi import FastAPI

from app.core.config import settings
from app.api.routes import documents


app = FastAPI(title=settings.APP_NAME)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }


app.include_router(documents.router)