from __future__ import annotations

import asyncio
from dataclasses import dataclass
from .models import EventStatus, IndustrialEvent, ProcessedEvent


@dataclass
class EventRecord:
    event: IndustrialEvent
    status: EventStatus
    result: ProcessedEvent | None = None
    error: str | None = None


class InMemoryEventStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._records: dict[str, EventRecord] = {}

    async def claim(self, event: IndustrialEvent) -> tuple[bool, EventRecord]:
        async with self._lock:
            record = self._records.get(event.event_id)
            if record:
                return False, record
            record = EventRecord(event=event, status=EventStatus.PROCESSING)
            self._records[event.event_id] = record
            return True, record

    async def succeed(self, event_id: str, result: ProcessedEvent) -> None:
        async with self._lock:
            record = self._records[event_id]
            record.status = EventStatus.SUCCEEDED
            record.result = result
            record.error = None

    async def fail(self, event_id: str, exc: Exception) -> None:
        async with self._lock:
            record = self._records[event_id]
            record.status = EventStatus.FAILED
            record.error = f"{type(exc).__name__}: {exc}"

    async def get(self, event_id: str) -> EventRecord | None:
        async with self._lock:
            return self._records.get(event_id)
