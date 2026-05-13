from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.mentor_action_service import draft_mentor_message

router = APIRouter(prefix="/mentor-actions", tags=["Mentor Actions"])


class DraftMessageRequest(BaseModel):
    newcomer_id: int
    signal_id: int | None = None
    tone: str = "supportive"


class DraftMessageResponse(BaseModel):
    message: str
    newcomer_name: str
    signal_title: str | None


@router.post("/draft-message", response_model=DraftMessageResponse)
def draft_message(payload: DraftMessageRequest, db: Session = Depends(get_db)):
    try:
        result = draft_mentor_message(
            db=db,
            newcomer_id=payload.newcomer_id,
            signal_id=payload.signal_id,
            tone=payload.tone,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DraftMessageResponse(**result)
