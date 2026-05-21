from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.demo_seed_service import reset_demo_data, reset_sales_demo_data, seed_demo_data

router = APIRouter(prefix="/demo", tags=["Demo"])


class SeedResponse(BaseModel):
    mentor_id: int | None = None
    newcomer_id: int | None = None
    newcomer_user_id: int | None = None
    newcomer_ids: list[int] = []
    personas: list[dict] = []
    plan_id: int | None = None
    signal_id: int | None = None
    documents_created: int | None = None
    courses_created: int | None = None
    tasks_created: int | None = None
    questions_created: int | None = None
    meetings_created: int | None = None
    signals_created: int | None = None
    blocked_reports_created: int | None = None
    already_seeded: bool = False


@router.post("/seed", response_model=SeedResponse)
def seed(db: Session = Depends(get_db)):
    result = seed_demo_data(db=db)
    return SeedResponse(**result)


@router.post("/reset", response_model=SeedResponse)
def reset(db: Session = Depends(get_db)):
    result = reset_demo_data(db=db)
    return SeedResponse(**result)


@router.post("/reset-sales", response_model=SeedResponse)
def reset_sales(db: Session = Depends(get_db)):
    result = reset_sales_demo_data(db=db)
    return SeedResponse(**result)
