import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.arena import ArenaScenario, ArenaSession, ArenaMessage
from app.models.ai_signal import AISignal
from app.services.arena_streaming import call_json_async, load_arena_prompt


RADAR_DIMENSIONS = [
    "opening",
    "discovery",
    "objections",
    "closing",
    "product_knowledge",
]

WEAK_THRESHOLD = 50
WEAK_SESSIONS_REQUIRED = 3
LOOKBACK_SESSIONS = 5


def _format_persona(scenario: ArenaScenario) -> str:
    persona = scenario.persona or {}
    return (
        f"{persona.get('name', '?')} ({persona.get('role', '?')} at "
        f"{persona.get('company', '?')}). Traits: "
        f"{', '.join(persona.get('traits') or [])}. "
        f"Hidden agenda: {persona.get('hidden_agenda', '(none)')}. "
        f"Mood: {persona.get('emotional_state', 'neutral')}."
    )


def _format_transcript(messages: list[ArenaMessage]) -> str:
    parts = []
    for msg in messages:
        who = "SELLER" if msg.sender == "newcomer" else "CLIENT"
        line = f"[id={msg.id}] {who}: {msg.content}"
        if msg.ai_analysis:
            color = msg.ai_analysis.get("color")
            label = msg.ai_analysis.get("label")
            if color or label:
                line += f"  (current: {color or '-'} / {label or '-'})"
        parts.append(line)
    return "\n".join(parts) if parts else "(no messages)"


def _clamp_score(value) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, v))


def _normalize_debrief(raw: dict, session_id: int) -> dict:
    radar = raw.get("radar_scores") or {}
    radar_scores = {dim: _clamp_score(radar.get(dim, 0)) for dim in RADAR_DIMENSIONS}

    transcript_review = []
    for entry in raw.get("transcript_review") or []:
        color = entry.get("color", "neutral")
        if color not in {"green", "yellow", "red", "neutral"}:
            color = "neutral"
        alternatives = []
        if color == "red":
            for alt in (entry.get("alternatives") or [])[:3]:
                alternatives.append(
                    {
                        "text": (alt.get("text") or "").strip(),
                        "why": (alt.get("why") or "").strip(),
                        "citation_doc_id": alt.get("citation_doc_id"),
                        "citation_title": alt.get("citation_title"),
                    }
                )
        transcript_review.append(
            {
                "message_id": entry.get("message_id"),
                "color": color,
                "label": (entry.get("label") or "").strip(),
                "dimension": entry.get("dimension"),
                "alternatives": alternatives,
            }
        )

    badges = []
    for badge in (raw.get("badges") or [])[:5]:
        code = (badge.get("code") or "").strip()
        if not code:
            continue
        badges.append(
            {
                "code": code,
                "label": (badge.get("label") or code).strip(),
                "emoji": (badge.get("emoji") or "🏅").strip(),
                "description": (badge.get("description") or "").strip(),
            }
        )

    return {
        "session_id": session_id,
        "overall_score": _clamp_score(raw.get("overall_score", 0)),
        "radar_scores": radar_scores,
        "headline": (raw.get("headline") or "Session complete").strip()[:140],
        "summary": (raw.get("summary") or "").strip(),
        "strongest_dimension": raw.get("strongest_dimension")
        if raw.get("strongest_dimension") in RADAR_DIMENSIONS
        else None,
        "weakest_dimension": raw.get("weakest_dimension")
        if raw.get("weakest_dimension") in RADAR_DIMENSIONS
        else None,
        "next_step": (raw.get("next_step") or "").strip(),
        "badges": badges,
        "transcript_review": transcript_review,
    }


def _apply_review_to_messages(db: Session, session: ArenaSession, debrief: dict) -> None:
    by_id = {msg.id: msg for msg in session.messages}
    for entry in debrief.get("transcript_review", []):
        msg = by_id.get(entry.get("message_id"))
        if not msg:
            continue
        analysis = dict(msg.ai_analysis or {})
        analysis["color"] = entry.get("color") or analysis.get("color")
        analysis["label"] = entry.get("label") or analysis.get("label")
        analysis["dimension"] = entry.get("dimension") or analysis.get("dimension")
        analysis["alternatives"] = entry.get("alternatives") or []
        msg.ai_analysis = analysis
        msg.color = entry.get("color") or msg.color


def _build_transcript_response(session: ArenaSession, debrief: dict) -> list[dict]:
    review_by_msg = {
        e.get("message_id"): e for e in debrief.get("transcript_review", [])
    }
    out = []
    for msg in session.messages:
        review = review_by_msg.get(msg.id)
        if msg.sender == "client":
            continue
        out.append(
            {
                "message_id": msg.id,
                "sender": msg.sender,
                "content": msg.content,
                "color": (review or {}).get("color") or msg.color or "neutral",
                "label": (review or {}).get("label"),
                "dimension": (review or {}).get("dimension"),
                "alternatives": (review or {}).get("alternatives") or [],
            }
        )
    return out


def _maybe_fire_arena_signal(
    db: Session,
    session: ArenaSession,
    debrief: dict,
) -> None:
    """
    Auto-fire an AISignal if the same dimension has been weak across enough recent sessions.
    """
    weakest = debrief.get("weakest_dimension")
    if not weakest:
        return

    recent = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id == session.newcomer_id)
        .filter(ArenaSession.status == "ended")
        .order_by(ArenaSession.id.desc())
        .limit(LOOKBACK_SESSIONS)
        .all()
    )

    weak_count = 0
    weak_scores = []
    for s in recent:
        scores = (s.radar_scores or {})
        value = scores.get(weakest)
        if isinstance(value, (int, float)) and value < WEAK_THRESHOLD:
            weak_count += 1
            weak_scores.append(int(value))

    if weak_count < WEAK_SESSIONS_REQUIRED:
        return

    signal_type = f"arena_low_{weakest}"
    existing = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == session.newcomer_id)
        .filter(AISignal.signal_type == signal_type)
        .filter(AISignal.status == "open")
        .first()
    )

    evidence = (
        f"Last {len(recent)} arena sessions: "
        f"{weak_count} below {WEAK_THRESHOLD} on '{weakest}'. "
        f"Recent scores: {weak_scores}."
    )
    title = f"Arena weakness: {weakest.replace('_', ' ').title()}"
    description = (
        f"{session.newcomer.user.full_name if session.newcomer and session.newcomer.user else 'Newcomer'} "
        f"has scored below {WEAK_THRESHOLD} on {weakest.replace('_', ' ')} "
        f"in {weak_count} of last {len(recent)} arena sessions."
    )
    suggested = (
        f"Open a 15-min coaching block focused on {weakest.replace('_', ' ')}. "
        f"Consider assigning a higher-difficulty arena scenario in this dimension."
    )

    now = datetime.now(timezone.utc)
    if existing:
        existing.severity = "high" if weak_count >= 4 else "medium"
        existing.confidence = 0.85
        existing.score = float(weak_count) / max(1, len(recent))
        existing.tone = "attention"
        existing.title = title
        existing.description = description
        existing.evidence = evidence
        existing.suggested_action = suggested
        existing.occurrence_count = (existing.occurrence_count or 0) + 1
        existing.last_seen_at = now
    else:
        signal = AISignal(
            newcomer_id=session.newcomer_id,
            signal_type=signal_type,
            severity="high" if weak_count >= 4 else "medium",
            confidence=0.85,
            score=float(weak_count) / max(1, len(recent)),
            tone="attention",
            title=title,
            description=description,
            evidence=evidence,
            suggested_action=suggested,
            status="open",
            occurrence_count=1,
            target_scope=None,
            last_seen_at=now,
        )
        db.add(signal)
    db.flush()


def fallback_debrief(session: ArenaSession) -> dict:
    msgs = [m for m in session.messages if m.sender == "newcomer"]
    avg = 60
    return {
        "session_id": session.id,
        "overall_score": avg,
        "radar_scores": {dim: avg for dim in RADAR_DIMENSIONS},
        "headline": "Session complete — quick recap below.",
        "summary": "We logged the session. The AI coach is offline; manual review recommended.",
        "strongest_dimension": "opening",
        "weakest_dimension": "objections",
        "next_step": "Try a higher-difficulty discovery scenario next.",
        "badges": [],
        "transcript_review": [
            {
                "message_id": m.id,
                "color": "yellow",
                "label": "logged",
                "dimension": "discovery",
                "alternatives": [],
            }
            for m in msgs
        ],
    }


async def generate_debrief(
    db: Session,
    session: ArenaSession,
    kb_context: str = "",
) -> dict:
    scenario = session.scenario
    template = load_arena_prompt("arena_debrief.txt")
    prompt = template.format(
        scenario_title=scenario.title,
        conversation_type=scenario.conversation_type,
        difficulty=scenario.difficulty,
        goal_text=scenario.goal_text or "(no explicit goal)",
        success_criteria=", ".join(scenario.success_criteria or []) or "(none)",
        persona_summary=_format_persona(scenario),
        kb_context=kb_context or "(no documents indexed)",
        transcript=_format_transcript(list(session.messages)),
    )

    try:
        raw = await call_json_async(prompt, temperature=0.4)
        if not raw:
            raise ValueError("empty debrief")
        debrief = _normalize_debrief(raw, session.id)
    except Exception:
        debrief = fallback_debrief(session)

    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)
    session.overall_score = debrief["overall_score"]
    session.radar_scores = debrief["radar_scores"]
    session.badges_earned = debrief["badges"]
    session.summary = debrief["headline"]
    session.debrief = debrief

    _apply_review_to_messages(db, session, debrief)
    _maybe_fire_arena_signal(db, session, debrief)

    db.flush()
    db.commit()

    transcript_response = _build_transcript_response(session, debrief)

    return {
        **debrief,
        "transcript": transcript_response,
    }
