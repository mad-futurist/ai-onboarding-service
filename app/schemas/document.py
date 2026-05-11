from datetime import datetime
from pydantic import BaseModel


class DocumentCreate(BaseModel):
    title: str
    content: str
    source: str | None = None


class DocumentRead(BaseModel):
    id: int
    title: str
    content: str
    source: str | None
    created_at: datetime

    class Config:
        from_attributes = True