from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    newcomer_profile = relationship(
        "NewcomerProfile",
        back_populates="user",
        foreign_keys="NewcomerProfile.user_id",
        uselist=False,
    )

    mentored_newcomers = relationship(
        "NewcomerProfile",
        back_populates="mentor",
        foreign_keys="NewcomerProfile.mentor_id",
    )