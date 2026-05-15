from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)

    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    index = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    infographic_url = Column(String(1024), nullable=True)
    infographic_kind = Column(String(50), nullable=True)  # mermaid | svg | png
    infographic_source = Column(Text, nullable=True)      # raw mermaid/svg source

    source_document_ids = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    course = relationship("Course", back_populates="lessons")
