from sqlalchemy.orm import Session

from app.models.arena import ArenaScenario, ArenaSession
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.services.arena_streaming import call_json_async, load_arena_prompt


ALLOWED_CONVERSATION_TYPES = {
    "discovery",
    "objection_handling",
    "closing",
    "technical",
}


def _aggregate_radar(sessions: list[ArenaSession]) -> dict:
    dims = ["opening", "discovery", "objections", "closing", "product_knowledge"]
    totals = {d: 0.0 for d in dims}
    counts = {d: 0 for d in dims}
    for s in sessions:
        radar = s.radar_scores or {}
        for d in dims:
            v = radar.get(d)
            if isinstance(v, (int, float)):
                totals[d] += float(v)
                counts[d] += 1
    return {d: round(totals[d] / counts[d], 1) if counts[d] else 0.0 for d in dims}


def _normalize_persona(raw: dict) -> dict:
    title = (raw.get("title") or "Personal Bot").strip()[:120]

    ctype = raw.get("conversation_type", "discovery")
    if ctype not in ALLOWED_CONVERSATION_TYPES:
        ctype = "discovery"

    try:
        difficulty = int(raw.get("difficulty", 3))
    except (TypeError, ValueError):
        difficulty = 3
    difficulty = max(3, min(5, difficulty))

    persona_in = raw.get("persona") or {}
    persona = {
        "name": (persona_in.get("name") or "Anonymous Client").strip()[:100],
        "role": (persona_in.get("role") or "Decision maker").strip()[:120],
        "company": (persona_in.get("company") or "ACME Corp").strip()[:120],
        "traits": [str(t).strip()[:40] for t in (persona_in.get("traits") or [])][:6],
        "hidden_agenda": (persona_in.get("hidden_agenda") or "").strip()[:280],
        "emotional_state": (persona_in.get("emotional_state") or "neutral").strip()[:80],
        "voice_notes": (persona_in.get("voice_notes") or "").strip()[:200],
        "pet_peeves": [str(p).strip()[:40] for p in (persona_in.get("pet_peeves") or [])][:5],
    }

    description = (raw.get("description") or "").strip()[:280]
    cover_emoji = (raw.get("cover_emoji") or "🤖").strip()[:8]
    goal_text = (raw.get("goal_text") or "").strip()[:280]
    success_criteria = [
        str(c).strip()[:140] for c in (raw.get("success_criteria") or [])
    ][:5]

    return {
        "title": title,
        "conversation_type": ctype,
        "difficulty": difficulty,
        "persona": persona,
        "description": description,
        "cover_emoji": cover_emoji,
        "goal_text": goal_text,
        "success_criteria": success_criteria,
    }


def _fallback(newcomer: NewcomerProfile, focus: list[str]) -> dict:
    focus_label = focus[0] if focus else "discovery"
    return {
        "title": f"Personal Bot — {focus_label.replace('_', ' ').title()}",
        "conversation_type": "discovery" if focus_label != "closing" else "closing",
        "difficulty": 4,
        "persona": {
            "name": "Jordan Pierce",
            "role": "VP Operations",
            "company": "Northridge Logistics",
            "traits": ["skeptical", "time-pressed", "data-driven"],
            "hidden_agenda": "Needs internal political cover to approve a vendor.",
            "emotional_state": "guarded",
            "voice_notes": "Short sentences. Asks for numbers.",
            "pet_peeves": ["vague promises", "buzzwords"],
        },
        "description": "A skeptical buyer who tests every claim.",
        "cover_emoji": "🤖",
        "goal_text": f"Make real progress on {focus_label.replace('_', ' ')} without losing the call.",
        "success_criteria": [
            "Discover at least 2 concrete pains",
            "Earn a follow-up meeting",
        ],
    }


def _build_kb_context(db: Session, source_ids: list[int]) -> str:
    if not source_ids:
        return "(no documents selected)"
    docs = db.query(Document).filter(Document.id.in_(source_ids)).all()
    if not docs:
        return "(no documents selected)"
    parts = []
    for d in docs:
        body = (d.content or "")[:1200]
        parts.append(
            f"DOC ID: {d.id}\nTITLE: {d.title}\nTYPE: {d.document_type or 'doc'}\nCONTENT:\n{body}"
        )
    return "\n\n---\n\n".join(parts)


async def build_personal_bot_spec(
    db: Session,
    newcomer: NewcomerProfile,
    focus_dimensions: list[str],
    pain_text: str,
    source_ids: list[int],
) -> dict:
    """
    Returns a JSON spec (without persisting) so the trainee can edit before saving.
    """
    sessions = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id == newcomer.id)
        .order_by(ArenaSession.id.desc())
        .limit(10)
        .all()
    )
    radar = _aggregate_radar(sessions)
    kb_context = _build_kb_context(db, source_ids)

    template = load_arena_prompt("arena_personal_bot.txt")
    prompt = template.format(
        job_title=newcomer.job_title or "Sales rep",
        team=newcomer.team or "Sales",
        radar_scores=", ".join(f"{k}={v}" for k, v in radar.items()),
        pain_text=(pain_text or "(none)").strip()[:280],
        focus_dimensions=", ".join(focus_dimensions) or "(let model decide)",
        kb_context=kb_context,
    )
    try:
        raw = await call_json_async(prompt, temperature=0.7)
        if not raw:
            raise ValueError("empty bot spec")
        return _normalize_persona(raw)
    except Exception:
        return _fallback(newcomer, focus_dimensions)


def persist_spec(
    db: Session,
    newcomer: NewcomerProfile,
    spec: dict,
    source_ids: list[int] | None = None,
) -> ArenaScenario:
    scenario = ArenaScenario(
        mentor_id=newcomer.mentor_id,
        audience_newcomer_id=newcomer.id,
        title=spec["title"],
        conversation_type=spec["conversation_type"],
        difficulty=spec["difficulty"],
        persona=spec["persona"],
        goal_text=spec.get("goal_text"),
        success_criteria=spec.get("success_criteria") or [],
        kb_source_ids=source_ids or [],
        allow_live_coaching=False,
        is_personal_bot=True,
        description=spec.get("description"),
        cover_emoji=spec.get("cover_emoji"),
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


async def generate_personal_bot(
    db: Session,
    newcomer: NewcomerProfile,
    focus_dimensions: list[str],
    pain_text: str,
    kb_context: str = "",
) -> ArenaScenario:
    sessions = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id == newcomer.id)
        .order_by(ArenaSession.id.desc())
        .limit(10)
        .all()
    )
    radar = _aggregate_radar(sessions)

    template = load_arena_prompt("arena_personal_bot.txt")
    prompt = template.format(
        job_title=newcomer.job_title or "Sales rep",
        team=newcomer.team or "Sales",
        radar_scores=", ".join(f"{k}={v}" for k, v in radar.items()),
        pain_text=(pain_text or "(none)").strip()[:280],
        focus_dimensions=", ".join(focus_dimensions) or "(let model decide)",
        kb_context=kb_context or "(no documents indexed)",
    )

    try:
        raw = await call_json_async(prompt, temperature=0.7)
        if not raw:
            raise ValueError("empty bot spec")
        spec = _normalize_persona(raw)
    except Exception:
        spec = _fallback(newcomer, focus_dimensions)

    scenario = ArenaScenario(
        mentor_id=newcomer.mentor_id,
        audience_newcomer_id=newcomer.id,
        title=spec["title"],
        conversation_type=spec["conversation_type"],
        difficulty=spec["difficulty"],
        persona=spec["persona"],
        goal_text=spec["goal_text"],
        success_criteria=spec["success_criteria"],
        kb_source_ids=[],
        allow_live_coaching=False,
        is_personal_bot=True,
        description=spec["description"],
        cover_emoji=spec["cover_emoji"],
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario
