from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)
    document_type = Column(String(100), nullable=True)

    domain = Column(String(100), nullable=True)        # technical | hr | process | architecture | other
    role_target = Column(String(255), nullable=True)   # backend_developer | qa | all | etc.
    scope = Column(String(50), nullable=True)          # enterprise | team | role

    source_type = Column(String(20), nullable=True)    # text | url | github_link | gitlab_link
    external_url = Column(String(1024), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )