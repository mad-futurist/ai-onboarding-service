from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


ContextType = Literal["document", "task"]


class AIAskRequest(BaseModel):
    question: str = Field(min_length=3)
    user_id: int | None = None
    newcomer_id: int | None = None
    top_k: int = 4
    conversation_id: int | None = None
    context_type: ContextType | None = None
    context_id: int | None = None


class AISourceRead(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    content_preview: str
    similarity: float

    class Config:
        from_attributes = True


class AIAskResponse(BaseModel):
    question_id: int
    question: str
    answer: str
    sources: list[AISourceRead]
    conversation_id: int | None = None


class AIQuestionRead(BaseModel):
    id: int
    user_id: int | None
    newcomer_id: int | None
    conversation_id: int | None = None
    question: str
    answer: str
    status: str
    created_at: datetime
    sources: list[AISourceRead] = []

    class Config:
        from_attributes = True


class AIConversationCreate(BaseModel):
    user_id: int | None = None
    newcomer_id: int | None = None
    title: str | None = None
    context_type: ContextType | None = None
    context_id: int | None = None


class AIConversationRead(BaseModel):
    id: int
    user_id: int | None
    newcomer_id: int | None
    title: str
    context_type: ContextType | None
    context_id: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIConversationDetail(AIConversationRead):
    questions: list[AIQuestionRead] = []
