from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.db.base import Base


class CompanyOnboardingGap(Base):
    __tablename__ = "company_onboarding_gaps"

    id = Column(Integer, primary_key=True, index=True)

    gap_type = Column(String(100), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)

    affected_newcomers_count = Column(Integer, nullable=False, default=0)

    suggested_fix = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="open")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
