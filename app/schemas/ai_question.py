from datetime import datetime
from pydantic import BaseModel, Field


class DocumentChunkGenerateResponse(BaseModel):
    document_id: int
    chunks_created: int


class AIAskRequest(BaseModel):
    question: str = Field(min_length=3)
    user_id: int | None = None
    newcomer_id: int | None = None
    top_k: int = 4


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


class AIQuestionRead(BaseModel):
    id: int
    user_id: int | None
    newcomer_id: int | None
    question: str
    answer: str
    status: str
    created_at: datetime
    sources: list[AISourceRead] = []

    class Config:
        from_attributes = True