from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.ai_answer_feedback import AIAnswerFeedback
from app.models.ai_conversation import AIConversation
from app.models.document import Document
from app.models.ai_question import AIQuestion
from app.models.newcomer import NewcomerProfile
from app.schemas.ai_answer_feedback import AIAnswerFeedbackCreate, AIAnswerFeedbackRead
from app.schemas.ai_question import (
    AIAskRequest,
    AIAskResponse,
    AIConversationCreate,
    AIConversationDetail,
    AIConversationRead,
    AIQuestionRead,
    AISourceRead,
    ContextType,
)
from app.schemas.document_chunk import DocumentChunkGenerateResponse
from app.services.ai_answer_feedback_service import create_feedback
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
        conversation_id=payload.conversation_id,
        context_type=payload.context_type,
        context_id=payload.context_id,
    )

    return AIAskResponse(
        question_id=ai_question.id,
        question=ai_question.question,
        answer=ai_question.answer,
        conversation_id=ai_question.conversation_id,
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


@router.post("/questions/{question_id}/feedback", response_model=AIAnswerFeedbackRead, status_code=201)
def submit_answer_feedback(
    question_id: int,
    payload: AIAnswerFeedbackCreate,
    db: Session = Depends(get_db),
):
    question = db.query(AIQuestion).filter(AIQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="AI question not found")

    return create_feedback(
        db=db,
        question_id=question_id,
        feedback_type=payload.feedback_type,
        user_id=payload.user_id,
        newcomer_id=payload.newcomer_id,
        rating=payload.rating,
        comment=payload.comment,
    )


@router.get("/feedback/", response_model=list[AIAnswerFeedbackRead])
def list_answer_feedbacks(db: Session = Depends(get_db)):
    return db.query(AIAnswerFeedback).order_by(AIAnswerFeedback.id.desc()).all()


@router.get("/conversations", response_model=list[AIConversationRead])
def list_conversations(
    newcomer_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    context_type: ContextType | None = Query(default=None),
    context_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(AIConversation)

    if newcomer_id is not None:
        query = query.filter(AIConversation.newcomer_id == newcomer_id)
    if user_id is not None:
        query = query.filter(AIConversation.user_id == user_id)
    if context_type is not None:
        query = query.filter(AIConversation.context_type == context_type)
    if context_id is not None:
        query = query.filter(AIConversation.context_id == context_id)

    return query.order_by(AIConversation.updated_at.desc()).all()


@router.post("/conversations", response_model=AIConversationRead, status_code=201)
def create_conversation(
    payload: AIConversationCreate,
    db: Session = Depends(get_db),
):
    conversation = AIConversation(
        user_id=payload.user_id,
        newcomer_id=payload.newcomer_id,
        title=payload.title or "New conversation",
        context_type=payload.context_type,
        context_id=payload.context_id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetail)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = (
        db.query(AIConversation)
        .options(joinedload(AIConversation.questions).joinedload(AIQuestion.sources))
        .filter(AIConversation.id == conversation_id)
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = (
        db.query(AIConversation)
        .filter(AIConversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()
    return Response(status_code=204)


@router.get("/feedback/newcomers/{newcomer_id}", response_model=list[AIAnswerFeedbackRead])
def list_answer_feedbacks_for_newcomer(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    return (
        db.query(AIAnswerFeedback)
        .filter(AIAnswerFeedback.newcomer_id == newcomer_id)
        .order_by(AIAnswerFeedback.id.desc())
        .all()
    )