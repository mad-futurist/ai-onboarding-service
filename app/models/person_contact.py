from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, func

from app.db.base import Base


class PersonContact(Base):
    __tablename__ = "person_contacts"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    team = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    topics = Column(JSON, nullable=True)  # list[str]

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewcomerRecommendedContact(Base):
    __tablename__ = "newcomer_recommended_contacts"

    id = Column(Integer, primary_key=True, index=True)

    newcomer_id = Column(Integer, ForeignKey("newcomer_profiles.id"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("person_contacts.id"), nullable=False, index=True)

    reason = Column(Text, nullable=False)
    topic = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
