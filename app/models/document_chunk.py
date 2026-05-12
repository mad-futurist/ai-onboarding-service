from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base
from app.core.config import settings


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    token_estimate = Column(Integer, nullable=False, default=0)

    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=False)

    source_title = Column(String(255), nullable=True)
    source_type = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship(
        "Document",
        back_populates="chunks",
    )