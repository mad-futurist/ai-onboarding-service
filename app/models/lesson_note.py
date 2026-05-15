from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, UniqueConstraint, func

from app.db.base import Base


class LessonNote(Base):
    __tablename__ = "lesson_notes"
    __table_args__ = (
        UniqueConstraint("newcomer_id", "lesson_id", name="uq_lesson_notes_newcomer_lesson"),
    )

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    body = Column(Text, nullable=False, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
