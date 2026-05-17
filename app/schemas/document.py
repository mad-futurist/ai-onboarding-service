from datetime import datetime
from pydantic import BaseModel

from app.schemas.document_chunk import DocumentChunkRead


class DocumentCreate(BaseModel):
    title: str
    content: str = ""
    source: str | None = None
    document_type: str | None = None
    domain: str | None = None
    role_target: str | None = None
    scope: str | None = None
    source_type: str | None = None
    external_url: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    source: str | None = None
    document_type: str | None = None
    domain: str | None = None
    role_target: str | None = None
    scope: str | None = None
    source_type: str | None = None
    external_url: str | None = None


class DocumentRead(BaseModel):
    id: int
    title: str
    content: str
    source: str | None
    document_type: str | None
    domain: str | None
    role_target: str | None
    scope: str | None
    source_type: str | None = None
    external_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: int
    title: str
    source: str | None
    document_type: str | None
    domain: str | None
    role_target: str | None
    scope: str | None
    source_type: str | None = None
    external_url: str | None = None
    is_recommended: bool = False
    recommendation_reason: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentWithChunksRead(DocumentRead):
    chunks: list[DocumentChunkRead] = []


class KnowledgeBaseGroupItem(BaseModel):
    domain: str | None
    scope: str | None
    documents: list[DocumentListItem]


class KnowledgeBaseResponse(BaseModel):
    total: int
    groups: list[KnowledgeBaseGroupItem]


class DocumentClassifyRequest(BaseModel):
    content: str
    title: str | None = None


class DocumentClassifyResponse(BaseModel):
    title: str
    summary: str
    domain: str
    document_type: str
    source_type: str
