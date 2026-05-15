from datetime import datetime
from pydantic import BaseModel


class LessonNoteUpsert(BaseModel):
    body: str


class LessonNoteRead(BaseModel):
    id: int
    newcomer_id: int
    lesson_id: int
    body: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
