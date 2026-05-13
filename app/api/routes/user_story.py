from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user_story import UserStoryResponse
from app.services.user_story_service import get_user_story

router = APIRouter(prefix="/story", tags=["User Story"])


@router.get("/newcomers/{newcomer_id}", response_model=UserStoryResponse)
def get_newcomer_story(newcomer_id: int, db: Session = Depends(get_db)):
    try:
        return get_user_story(db=db, newcomer_id=newcomer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
