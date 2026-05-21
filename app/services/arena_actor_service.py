from typing import Any, Iterable

from app.models.arena import ArenaScenario, ArenaMessage
from app.services.arena_streaming import load_arena_prompt, stream_chat_tokens_async


def _format_list(value: Any) -> str:
    if not value:
        return "(none)"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def build_actor_system_prompt(
    scenario: ArenaScenario,
    kb_context: str = "",
) -> str:
    persona = scenario.persona or {}
    template = load_arena_prompt("arena_client_actor.txt")
    return template.format(
        persona_name=persona.get("name", "Client"),
        persona_role=persona.get("role", "Decision maker"),
        persona_company=persona.get("company", "ACME Corp"),
        persona_traits=_format_list(persona.get("traits")),
        persona_hidden_agenda=persona.get("hidden_agenda", "(none)"),
        persona_emotional_state=persona.get("emotional_state", "neutral"),
        persona_voice_notes=persona.get("voice_notes", "professional"),
        persona_pet_peeves=_format_list(persona.get("pet_peeves")),
        conversation_type=scenario.conversation_type or "discovery",
        difficulty=scenario.difficulty or 1,
        kb_context=kb_context or "(no documents indexed)",
    )


def history_for_actor(messages: Iterable[ArenaMessage]) -> list[dict]:
    out: list[dict] = []
    for msg in messages:
        if msg.sender == "newcomer":
            out.append({"role": "user", "content": msg.content})
        elif msg.sender == "client":
            out.append({"role": "assistant", "content": msg.content})
    return out


async def stream_actor_response(
    scenario: ArenaScenario,
    history_msgs: list[ArenaMessage],
    seller_message: str,
    kb_context: str = "",
):
    system_prompt = build_actor_system_prompt(scenario, kb_context=kb_context)
    history = history_for_actor(history_msgs)
    async for piece in stream_chat_tokens_async(system_prompt, history, seller_message):
        yield piece
