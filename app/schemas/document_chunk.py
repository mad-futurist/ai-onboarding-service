from datetime import datetime
from pydantic import BaseModel


class DocumentChunkRead(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    token_estimate: int
    source_title: str | None
    source_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkListItem(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    token_estimate: int
    source_title: str | None
    source_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkGenerateResponse(BaseModel):
    document_id: int
    chunks_created: int