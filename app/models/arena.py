from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class ArenaScenario(Base):
    __tablename__ = "arena_scenarios"

    id = Column(Integer, primary_key=True, index=True)

    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    audience_newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(255), nullable=False)
    conversation_type = Column(String(50), nullable=False, default="discovery")
    difficulty = Column(Integer, nullable=False, default=1)

    persona = Column(JSON, nullable=False, default=dict)
    goal_text = Column(Text, nullable=True)
    success_criteria = Column(JSON, nullable=True)
    kb_source_ids = Column(JSON, nullable=True)

    allow_live_coaching = Column(Boolean, nullable=False, default=True)
    is_personal_bot = Column(Boolean, nullable=False, default=False, index=True)

    description = Column(Text, nullable=True)
    cover_emoji = Column(String(8), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship(
        "ArenaSession",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )


class ArenaSession(Base):
    __tablename__ = "arena_sessions"

    id = Column(Integer, primary_key=True, index=True)

    scenario_id = Column(
        Integer,
        ForeignKey("arena_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    newcomer_id = Column(
        Integer,
        ForeignKey("newcomer_profiles.id"),
        nullable=False,
        index=True,
    )

    status = Column(String(20), nullable=False, default="active", index=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    overall_score = Column(Float, nullable=True)
    radar_scores = Column(JSON, nullable=True)
    badges_earned = Column(JSON, nullable=True)

    summary = Column(Text, nullable=True)
    debrief = Column(JSON, nullable=True)

    scenario = relationship("ArenaScenario", back_populates="sessions")
    newcomer = relationship("NewcomerProfile", back_populates="arena_sessions")
    messages = relationship(
        "ArenaMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ArenaMessage.order_index",
    )


class ArenaMessage(Base):
    __tablename__ = "arena_messages"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(
        Integer,
        ForeignKey("arena_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_index = Column(Integer, nullable=False, default=0)
    sender = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    ai_analysis = Column(JSON, nullable=True)
    color = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ArenaSession", back_populates="messages")
