from typing import Iterable

from app.models.arena import ArenaScenario, ArenaMessage
from app.services.arena_streaming import call_json_async, load_arena_prompt


ALLOWED_DIMENSIONS = {
    "opening",
    "discovery",
    "objections",
    "closing",
    "product_knowledge",
}
ALLOWED_COLORS = {"green", "yellow", "red"}


def _format_transcript(messages: Iterable[ArenaMessage], tail: int = 6) -> str:
    msgs = list(messages)[-tail:]
    parts = []
    for msg in msgs:
        who = "Seller" if msg.sender == "newcomer" else "Client"
        parts.append(f"{who}: {msg.content}")
    return "\n".join(parts) if parts else "(start of conversation)"


def _normalize(result: dict) -> dict:
    dimension = result.get("dimension", "discovery")
    if dimension not in ALLOWED_DIMENSIONS:
        dimension = "discovery"

    color = result.get("color", "yellow")
    if color not in ALLOWED_COLORS:
        color = "yellow"

    try:
        delta = int(result.get("delta", 0))
    except (TypeError, ValueError):
        delta = 0
    delta = max(-15, min(15, delta))

    label = (result.get("label") or "").strip()[:80] or "noted"
    why = (result.get("why") or "").strip()[:200]

    return {
        "dimension": dimension,
        "delta": delta,
        "label": label,
        "color": color,
        "why": why,
    }


async def analyze_seller_message(
    scenario: ArenaScenario,
    history_msgs: list[ArenaMessage],
    seller_message: str,
) -> dict:
    template = load_arena_prompt("arena_message_analyzer.txt")
    prompt = template.format(
        conversation_type=scenario.conversation_type or "discovery",
        goal_text=scenario.goal_text or "(no explicit goal)",
        success_criteria=", ".join(scenario.success_criteria or []) or "(none)",
        recent_transcript=_format_transcript(history_msgs),
        seller_message=seller_message.replace('"', "'"),
    )
    raw = await call_json_async(prompt, temperature=0.2)
    return _normalize(raw)


def fallback_analysis() -> dict:
    return {
        "dimension": "discovery",
        "delta": 0,
        "label": "neutral",
        "color": "yellow",
        "why": "Analyzer unavailable",
    }
