import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Iterable

import httpx
from openai import OpenAI

from app.core.config import settings


http_client = httpx.Client(verify=False)
client = OpenAI(http_client=http_client, api_key=settings.OPENAI_API_KEY)


def load_arena_prompt(name: str) -> str:
    return Path(f"app/prompts/{name}").read_text(encoding="utf-8")


def sse_frame(event: str, data: dict | str) -> bytes:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def stream_chat_tokens(
    system_prompt: str,
    history: Iterable[dict],
    user_message: str,
) -> Iterable[str]:
    """
    Synchronous generator that yields content deltas from an OpenAI streaming chat.
    The async generator wrapping this is responsible for offloading via to_thread.
    """
    messages = [{"role": "system", "content": system_prompt}]
    for entry in history:
        messages.append(entry)
    messages.append({"role": "user", "content": user_message})

    stream = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        stream=True,
        temperature=0.8,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


async def stream_chat_tokens_async(
    system_prompt: str,
    history: Iterable[dict],
    user_message: str,
) -> AsyncIterator[str]:
    """
    Async wrapper that pulls from the sync OpenAI stream on a worker thread so
    SSE generators don't block the event loop.
    """
    queue: asyncio.Queue = asyncio.Queue()
    sentinel = object()

    def producer():
        try:
            for piece in stream_chat_tokens(system_prompt, history, user_message):
                queue.put_nowait(piece)
        except Exception as exc:  # noqa: BLE001
            queue.put_nowait(("__error__", str(exc)))
        finally:
            queue.put_nowait(sentinel)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, producer)

    while True:
        item = await queue.get()
        if item is sentinel:
            return
        if isinstance(item, tuple) and item and item[0] == "__error__":
            raise RuntimeError(item[1])
        yield item


def call_json(prompt: str, *, temperature: float = 0.4) -> dict:
    """
    One-shot non-streaming JSON call.
    Falls back to {} if the model returns invalid JSON.
    """
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You return STRICT JSON only. No prose, no markdown fences.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


async def call_json_async(prompt: str, *, temperature: float = 0.4) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: call_json(prompt, temperature=temperature))
