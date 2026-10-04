from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class TraceEvent:
    trace_id: str
    stage: str
    status: str
    entity_id: str
    timestamp: str
    detail: str | None = None

    @classmethod
    def now(cls, trace_id: str, stage: str, status: str, entity_id: str, detail: str | None = None):
        return cls(
            trace_id=trace_id,
            stage=stage,
            status=status,
            entity_id=entity_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            detail=detail,
        )


class TraceSink(Protocol):
    def emit(self, event: TraceEvent) -> None: ...


class NullTraceSink:
    def emit(self, event: TraceEvent) -> None:
        del event


class ListTraceSink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)


class JsonLineTraceSink:
    def emit(self, event: TraceEvent) -> None:
        print(json.dumps(asdict(event), ensure_ascii=False, separators=(",", ":")))
