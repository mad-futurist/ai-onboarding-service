import asyncio
from collections import defaultdict


_session_queues: dict[int, list[asyncio.Queue]] = defaultdict(list)
_lock = asyncio.Lock()


async def subscribe(session_id: int) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    async with _lock:
        _session_queues[session_id].append(queue)
    return queue


async def unsubscribe(session_id: int, queue: asyncio.Queue) -> None:
    async with _lock:
        if queue in _session_queues.get(session_id, []):
            _session_queues[session_id].remove(queue)
        if session_id in _session_queues and not _session_queues[session_id]:
            del _session_queues[session_id]


async def publish(session_id: int, payload: dict) -> int:
    delivered = 0
    async with _lock:
        queues = list(_session_queues.get(session_id, []))
    for q in queues:
        await q.put(payload)
        delivered += 1
    return delivered
