from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.document import Document
from app.models.ai_question import AIQuestion
from app.schemas.ai_question import (
    DocumentChunkGenerateResponse,
    AIAskRequest,
    AIAskResponse,
    AIQuestionRead,
    AISourceRead,
)
from app.services.rag_service import generate_chunks_for_document, ask_ai_with_sources


router = APIRouter(prefix="/ai", tags=["AI Q&A"])


@router.post(
    "/documents/{document_id}/chunks/generate",
    response_model=DocumentChunkGenerateResponse,
)
def generate_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks_created = generate_chunks_for_document(
        db=db,
        document=document,
    )

    return DocumentChunkGenerateResponse(
        document_id=document.id,
        chunks_created=chunks_created,
    )


@router.post("/ask", response_model=AIAskResponse)
def ask_ai(
    payload: AIAskRequest,
    db: Session = Depends(get_db),
):
    if payload.top_k < 1 or payload.top_k > 10:
        raise HTTPException(
            status_code=400,
            detail="top_k must be between 1 and 10",
        )

    ai_question = ask_ai_with_sources(
        db=db,
        question=payload.question,
        user_id=payload.user_id,
        newcomer_id=payload.newcomer_id,
        top_k=payload.top_k,
    )

    return AIAskResponse(
        question_id=ai_question.id,
        question=ai_question.question,
        answer=ai_question.answer,
        sources=[
            AISourceRead(
                document_id=source.document_id,
                chunk_id=source.chunk_id,
                title=source.title,
                content_preview=source.content_preview,
                similarity=source.similarity,
            )
            for source in ai_question.sources
        ],
    )


@router.get("/questions/", response_model=list[AIQuestionRead])
def list_ai_questions(db: Session = Depends(get_db)):
    return (
        db.query(AIQuestion)
        .options(joinedload(AIQuestion.sources))
        .order_by(AIQuestion.id.desc())
        .all()
    )


@router.get("/questions/{question_id}", response_model=AIQuestionRead)
def get_ai_question(
    question_id: int,
    db: Session = Depends(get_db),
):
    ai_question = (
        db.query(AIQuestion)
        .options(joinedload(AIQuestion.sources))
        .filter(AIQuestion.id == question_id)
        .first()
    )

    if not ai_question:
        raise HTTPException(status_code=404, detail="AI question not found")

    return ai_question