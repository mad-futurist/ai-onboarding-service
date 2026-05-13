from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.schemas.document import DocumentListItem
from app.services.newcomer_kb_service import get_documents_for_newcomer, get_document_with_chunk_count
from app.services.rag_service import ask_ai_with_sources
from app.schemas.ai_question import AIAskResponse

router = APIRouter(prefix="/newcomer-kb", tags=["Newcomer Knowledge Base"])


class NewcomerDocumentRead(BaseModel):
    id: int
    title: str
    content: str
    domain: str | None
    scope: str | None
    role_target: str | None
    chunks_count: int

    class Config:
        from_attributes = True


class DocumentAskRequest(BaseModel):
    question: str
    user_id: int | None = None


@router.get("/{newcomer_id}/documents", response_model=list[DocumentListItem])
def list_newcomer_documents(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    try:
        return get_documents_for_newcomer(db=db, newcomer_id=newcomer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{newcomer_id}/documents/{document_id}", response_model=NewcomerDocumentRead)
def get_newcomer_document(newcomer_id: int, document_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    result = get_document_with_chunk_count(db=db, document_id=document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = result["document"]
    return NewcomerDocumentRead(
        id=doc.id,
        title=doc.title,
        content=doc.content,
        domain=doc.domain,
        scope=doc.scope,
        role_target=doc.role_target,
        chunks_count=result["chunks_count"],
    )


@router.post("/{newcomer_id}/documents/{document_id}/ask", response_model=AIAskResponse)
def ask_about_document(
    newcomer_id: int,
    document_id: int,
    payload: DocumentAskRequest,
    db: Session = Depends(get_db),
):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    ai_question = ask_ai_with_sources(
        db=db,
        question=payload.question,
        user_id=payload.user_id,
        newcomer_id=newcomer_id,
        top_k=4,
    )

    return ai_question
