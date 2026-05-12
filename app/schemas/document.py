from datetime import datetime
from pydantic import BaseModel

from app.schemas.document_chunk import DocumentChunkRead


class DocumentCreate(BaseModel):
    title: str
    content: str
    source: str | None = None
    document_type: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    source: str | None = None
    document_type: str | None = None


class DocumentRead(BaseModel):
    id: int
    title: str
    content: str
    source: str | None
    document_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: int
    title: str
    source: str | None
    document_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentWithChunksRead(DocumentRead):
    chunks: list[DocumentChunkRead] = []