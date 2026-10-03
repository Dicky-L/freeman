from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class PipelineEvent:
    trace_id: str
    stage: str
    status: str
    provider: str | None = None
    attempt: int | None = None
    latency_ms: int | None = None
    error_type: str | None = None


class EventSink(Protocol):
    def emit(self, event: PipelineEvent) -> None: ...


class NullEventSink:
    def emit(self, event: PipelineEvent) -> None:
        del event


class ListEventSink:
    """In-memory sink used by tests and demos."""

    def __init__(self) -> None:
        self.events: list[PipelineEvent] = []

    def emit(self, event: PipelineEvent) -> None:
        self.events.append(event)


class JsonLineEventSink:
    """Minimal structured logger; replaceable by Langfuse/OpenTelemetry in production."""

    def emit(self, event: PipelineEvent) -> None:
        print(json.dumps(asdict(event), ensure_ascii=False, separators=(",", ":")))
