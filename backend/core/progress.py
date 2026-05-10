"""
In-memory progress manager — replaces Redis pub/sub for local dev.
The pipeline publishes step events; the WebSocket endpoint subscribes and
forwards them to the browser in real time.
"""

import asyncio
from typing import Dict, List


class ProgressManager:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        # Buffer events so a WebSocket that connects slightly late still gets them
        self._history: Dict[str, List[dict]] = {}

    def subscribe(self, report_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        for past_event in self._history.get(report_id, []):
            q.put_nowait(past_event)
        self._subscribers.setdefault(report_id, []).append(q)
        return q

    def unsubscribe(self, report_id: str, queue: asyncio.Queue) -> None:
        listeners = self._subscribers.get(report_id, [])
        try:
            listeners.remove(queue)
        except ValueError:
            pass

    async def publish(self, report_id: str, event: dict) -> None:
        self._history.setdefault(report_id, []).append(event)
        for q in list(self._subscribers.get(report_id, [])):
            await q.put(event)

    def cleanup(self, report_id: str) -> None:
        self._subscribers.pop(report_id, None)
        self._history.pop(report_id, None)


# Singleton shared across the FastAPI process
progress = ProgressManager()
