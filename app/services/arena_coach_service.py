from typing import Any

from sqlalchemy.orm import Session

from app.models.arena import ArenaSession, ArenaMessage
from app.services.arena_streaming import call_json_async, load_arena_prompt


VALID_SKILLS = {"opening", "discovery", "objections", "closing", "product_knowledge"}


def _format_persona(session: ArenaSession) -> str:
    scenario = session.scenario
    persona = scenario.persona or {}
    return (
        f"{persona.get('name', '?')} ({persona.get('role', '?')} at "
        f"{persona.get('company', '?')}). Traits: "
        f"{', '.join(persona.get('traits') or [])}. "
        f"Mood: {persona.get('emotional_state', 'neutral')}. "
        f"Hidden agenda: {persona.get('hidden_agenda', '(none)')}."
    )


def _format_transcript(messages: list[ArenaMessage], target_id: int) -> str:
    sorted_msgs = sorted(messages, key=lambda m: m.order_index)
    target_idx = next(
        (i for i, m in enumerate(sorted_msgs) if m.id == target_id), len(sorted_msgs)
    )
    window = sorted_msgs[max(0, target_idx - 6) : target_idx + 1]
    parts = []
    for m in window:
        who = "SELLER" if m.sender == "newcomer" else "CLIENT"
        marker = "  <-- target" if m.id == target_id else ""
        parts.append(f"{who}: {m.content}{marker}")
    return "\n".join(parts) if parts else "(no prior context)"


def _normalize(raw: dict, sender: str) -> dict:
    moves = []
    for item in (raw.get("relationship_moves") or [])[:3]:
        title = (item.get("title") or "").strip()
        body = (item.get("body") or "").strip()
        if title or body:
            moves.append({"title": title[:60], "body": body[:240]})
    skill = raw.get("skill_focus")
    if skill not in VALID_SKILLS:
        skill = "discovery"
    return {
        "sender": "client" if sender == "client" else "newcomer",
        "headline": (raw.get("headline") or "Coach note").strip()[:120],
        "emotion_read": (raw.get("emotion_read") or "").strip()[:240]
        if sender == "client"
        else "",
        "relationship_moves": moves,
        "watch_out_for": (raw.get("watch_out_for") or "").strip()[:240],
        "better_response": (raw.get("better_response") or "").strip()[:400]
        if sender == "newcomer"
        else "",
        "skill_focus": skill,
    }


def _fallback(sender: str) -> dict:
    if sender == "client":
        return {
            "sender": "client",
            "headline": "Read the room",
            "emotion_read": "Client is likely curious but guarded — give them control of the conversation.",
            "relationship_moves": [
                {"title": "Mirror their tone", "body": "Match their cadence and energy before bringing new info."},
                {"title": "Earn the right", "body": "Ask one strong open question before any pitch."},
            ],
            "watch_out_for": "Pitching before they share at least one real pain point.",
            "better_response": "",
            "skill_focus": "discovery",
        }
    return {
        "sender": "newcomer",
        "headline": "Lead with discovery",
        "emotion_read": "",
        "relationship_moves": [
            {"title": "Ask, don't tell", "body": "Open with a question about their current process."},
            {"title": "Quantify the pain", "body": "Tie any product mention to a concrete metric they care about."},
        ],
        "watch_out_for": "Defaulting to feature dump.",
        "better_response": "What does your current workflow look like before [the moment of friction]? Where does it cost you the most time?",
        "skill_focus": "discovery",
    }


async def coach_message(
    db: Session,
    session: ArenaSession,
    target_message: ArenaMessage,
) -> dict:
    template = load_arena_prompt("arena_message_coach.txt")
    sender = "client" if target_message.sender == "client" else "newcomer"
    prompt = template.format(
        conversation_type=session.scenario.conversation_type or "discovery",
        goal_text=session.scenario.goal_text or "(no explicit goal)",
        difficulty=session.scenario.difficulty or 1,
        persona_summary=_format_persona(session),
        recent_transcript=_format_transcript(list(session.messages), target_message.id),
        sender=sender.upper(),
        message_content=target_message.content.replace('"', "'"),
    )
    try:
        raw = await call_json_async(prompt, temperature=0.4)
        if not raw:
            raise ValueError("empty coach response")
        return _normalize(raw, sender)
    except Exception:
        return _fallback(sender)
