from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.schemas.document import DocumentListItem
from app.services.knowledge_recommendation_service import get_recommendations

router = APIRouter(prefix="/knowledge", tags=["Knowledge Recommendations"])


class KnowledgeRecommendationItem(BaseModel):
    document: DocumentListItem
    priority: int
    reason: str

    class Config:
        from_attributes = True


@router.get("/recommendations/newcomers/{newcomer_id}", response_model=list[KnowledgeRecommendationItem])
def get_knowledge_recommendations(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    try:
        results = get_recommendations(db=db, newcomer_id=newcomer_id)
        return [
            KnowledgeRecommendationItem(document=r["document"], priority=r["priority"], reason=r["reason"])
            for r in results
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/recommendations/generate/newcomers/{newcomer_id}", response_model=list[KnowledgeRecommendationItem])
def generate_knowledge_recommendations(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    try:
        results = get_recommendations(db=db, newcomer_id=newcomer_id)
        return [
            KnowledgeRecommendationItem(document=r["document"], priority=r["priority"], reason=r["reason"])
            for r in results
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
