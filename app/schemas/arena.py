from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


RadarDimension = Literal[
    "opening",
    "discovery",
    "objections",
    "closing",
    "product_knowledge",
]

ConversationType = Literal[
    "discovery",
    "objection_handling",
    "closing",
    "technical",
]

MessageColor = Literal["green", "yellow", "red", "neutral"]


class RadarScore(BaseModel):
    opening: int = 0
    discovery: int = 0
    objections: int = 0
    closing: int = 0
    product_knowledge: int = 0


class PersonaDefinition(BaseModel):
    name: str
    role: Optional[str] = None
    company: Optional[str] = None
    traits: list[str] = Field(default_factory=list)
    hidden_agenda: Optional[str] = None
    emotional_state: Optional[str] = None
    voice_notes: Optional[str] = None
    pet_peeves: list[str] = Field(default_factory=list)


class ArenaScenarioCreate(BaseModel):
    mentor_id: Optional[int] = None
    audience_newcomer_id: Optional[int] = None
    title: str
    conversation_type: ConversationType = "discovery"
    difficulty: int = Field(default=1, ge=1, le=5)
    persona: PersonaDefinition
    goal_text: Optional[str] = None
    success_criteria: list[str] = Field(default_factory=list)
    kb_source_ids: list[int] = Field(default_factory=list)
    allow_live_coaching: bool = True
    description: Optional[str] = None
    cover_emoji: Optional[str] = None
    is_personal_bot: bool = False


class ArenaScenarioRead(BaseModel):
    id: int
    mentor_id: Optional[int]
    audience_newcomer_id: Optional[int]
    title: str
    conversation_type: str
    difficulty: int
    persona: dict[str, Any]
    goal_text: Optional[str]
    success_criteria: Optional[list[str] | dict[str, Any]]
    kb_source_ids: Optional[list[int]]
    allow_live_coaching: bool
    is_personal_bot: bool
    description: Optional[str]
    cover_emoji: Optional[str]
    created_at: datetime
    locked: bool = False
    attempts: int = 0
    last_score: Optional[float] = None

    class Config:
        from_attributes = True


class ArenaSessionStart(BaseModel):
    scenario_id: int
    newcomer_id: int


class ArenaSessionRead(BaseModel):
    id: int
    scenario_id: int
    newcomer_id: int
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    overall_score: Optional[float]
    radar_scores: Optional[dict[str, Any]]
    badges_earned: Optional[list[dict[str, Any]]]
    summary: Optional[str]

    class Config:
        from_attributes = True


class ArenaAnalysisFrame(BaseModel):
    dimension: RadarDimension
    delta: int
    label: str
    color: MessageColor = "neutral"
    why: Optional[str] = None


class ArenaMessageRead(BaseModel):
    id: int
    session_id: int
    order_index: int
    sender: str
    content: str
    ai_analysis: Optional[dict[str, Any]] = None
    color: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ArenaAlternative(BaseModel):
    text: str
    why: str
    citation_doc_id: Optional[int] = None
    citation_title: Optional[str] = None


class ArenaTranscriptEntry(BaseModel):
    message_id: int
    sender: str
    content: str
    color: MessageColor = "neutral"
    label: Optional[str] = None
    dimension: Optional[RadarDimension] = None
    alternatives: list[ArenaAlternative] = Field(default_factory=list)


class ArenaBadge(BaseModel):
    code: str
    label: str
    emoji: str = "🏅"
    description: Optional[str] = None


class ArenaDebriefRead(BaseModel):
    session_id: int
    overall_score: float
    radar_scores: RadarScore
    headline: str
    summary: str
    badges: list[ArenaBadge] = Field(default_factory=list)
    transcript: list[ArenaTranscriptEntry] = Field(default_factory=list)
    strongest_dimension: Optional[RadarDimension] = None
    weakest_dimension: Optional[RadarDimension] = None
    next_step: Optional[str] = None


class MentorHintCreate(BaseModel):
    text: str
    mentor_id: Optional[int] = None


class PersonalBotRequest(BaseModel):
    newcomer_id: int
    focus_dimensions: list[RadarDimension] = Field(default_factory=list)
    pain_text: Optional[str] = None


class ArenaLeaderboardEntry(BaseModel):
    newcomer_id: int
    name: str
    overall_score: float
    sessions_played: int
    streak: int = 0


class ArenaDashboardRead(BaseModel):
    sessions_this_week: int
    avg_score: float
    weakest_team_dimension: Optional[RadarDimension] = None
    leaderboard: list[ArenaLeaderboardEntry] = Field(default_factory=list)
    recent_sessions: list[ArenaSessionRead] = Field(default_factory=list)
    dimension_averages: dict[str, float] = Field(default_factory=dict)
    flagged_newcomer_ids: list[int] = Field(default_factory=list)


class NewcomerArenaSummary(BaseModel):
    newcomer_id: int
    sessions_played: int
    overall_score: float
    streak: int
    last_session_score: Optional[float] = None
    radar_scores: RadarScore = RadarScore()
    badges: list[ArenaBadge] = Field(default_factory=list)
