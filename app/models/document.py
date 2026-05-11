from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())