from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)

    plan_id = Column(
        Integer,
        ForeignKey("onboarding_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mentor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    role_target = Column(String(255), nullable=True, index=True)

    status = Column(String(50), nullable=False, default="draft")
    generated_by_ai = Column(Boolean, nullable=False, default=False)

    source_document_ids = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    lessons = relationship(
        "Lesson",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lesson.index",
    )
