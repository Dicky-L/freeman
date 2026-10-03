from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import StrEnum

from .models import CaregiverProfile
from .observability import EventSink, NullEventSink, PipelineEvent
from .reliable_llm import ReliableStructuredLLM


class JobStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class JobRecord:
    status: JobStatus
    result: CaregiverProfile | None = None
    error: str | None = None


class InMemoryJobStore:
    """Demonstrates atomic idempotency semantics."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, JobRecord] = {}

    async def claim(self, key: str) -> tuple[bool, JobRecord]:
        async with self._lock:
            existing = self._jobs.get(key)
            if existing:
                return False, existing
            record = JobRecord(status=JobStatus.RUNNING)
            self._jobs[key] = record
            return True, record

    async def succeed(self, key: str, result: CaregiverProfile) -> None:
        async with self._lock:
            self._jobs[key] = JobRecord(status=JobStatus.SUCCEEDED, result=result)

    async def fail(self, key: str, error: Exception) -> None:
        async with self._lock:
            self._jobs[key] = JobRecord(status=JobStatus.FAILED, error=str(error))

    async def get(self, key: str) -> JobRecord | None:
        async with self._lock:
            return self._jobs.get(key)


class ProfilePipeline:
    def __init__(
        self,
        llm: ReliableStructuredLLM[CaregiverProfile],
        store: InMemoryJobStore,
        *,
        events: EventSink | None = None,
    ) -> None:
        self._llm = llm
        self._store = store
        self._events = events or NullEventSink()

    async def process(self, idempotency_key: str, raw_profile: str) -> CaregiverProfile | None:
        claimed, record = await self._store.claim(idempotency_key)
        if not claimed:
            return record.result

        trace_id = uuid.uuid4().hex
        self._events.emit(PipelineEvent(trace_id=trace_id, stage="profile", status="started"))
        try:
            result = await self._llm.generate(
                "Extract a caregiver profile as strict JSON. Source:\n" + raw_profile,
                trace_id=trace_id,
            )
            await self._store.succeed(idempotency_key, result)
            self._events.emit(PipelineEvent(trace_id=trace_id, stage="profile", status="succeeded"))
            return result
        except Exception as exc:
            await self._store.fail(idempotency_key, exc)
            self._events.emit(
                PipelineEvent(
                    trace_id=trace_id,
                    stage="profile",
                    status="failed",
                    error_type=type(exc).__name__,
                )
            )
            raise
