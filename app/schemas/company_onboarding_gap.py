from datetime import datetime
from pydantic import BaseModel


class CompanyOnboardingGapRead(BaseModel):
    id: int
    gap_type: str
    topic: str
    title: str
    description: str
    evidence: str
    affected_newcomers_count: int
    suggested_fix: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyOnboardingGapDetectResponse(BaseModel):
    gaps_created: int
    gaps_updated: int
    gaps: list[CompanyOnboardingGapRead]


class CompanyOnboardingGapStatusResponse(BaseModel):
    id: int
    status: str

    class Config:
        from_attributes = True
