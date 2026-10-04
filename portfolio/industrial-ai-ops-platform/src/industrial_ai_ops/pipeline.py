from __future__ import annotations

import uuid
from datetime import datetime, timezone
from .freshness import is_stale
from .llm import StructuredAIEnricher
from .models import IndustrialEvent, ProcessedEvent
from .observability import NullTraceSink, TraceEvent, TraceSink
from .rules import evaluate_rules
from .store import InMemoryEventStore
from .workflow import InMemoryTaskCenter


class IndustrialAIPipeline:
    def __init__(
        self,
        store: InMemoryEventStore,
        task_center: InMemoryTaskCenter,
        enricher: StructuredAIEnricher,
        *,
        trace_sink: TraceSink | None = None,
        freshness_ttl_seconds: int = 300,
    ) -> None:
        self._store = store
        self._task_center = task_center
        self._enricher = enricher
        self._trace = trace_sink or NullTraceSink()
        self._ttl = freshness_ttl_seconds

    async def process(self, event: IndustrialEvent) -> ProcessedEvent | None:
        claimed, record = await self._store.claim(event)
        if not claimed:
            return record.result

        trace_id = uuid.uuid4().hex
        self._trace.emit(TraceEvent.now(trace_id, "ingest", "accepted", event.event_id))
        try:
            stale = is_stale(event.event_time, datetime.now(timezone.utc), self._ttl)
            decision = evaluate_rules(event)
            self._trace.emit(
                TraceEvent.now(trace_id, "rules", decision.severity.value, event.event_id, ",".join(decision.reason_codes))
            )

            enrichment = None
            if decision.requires_ai_enrichment:
                enrichment = await self._enricher.enrich(event)
                self._trace.emit(TraceEvent.now(trace_id, "ai", "validated", event.event_id))

            task_id = None
            if decision.requires_workflow_task:
                task = await self._task_center.create_task(event, decision)
                task_id = task.task_id
                self._trace.emit(TraceEvent.now(trace_id, "workflow", "task-created", event.event_id, task_id))

            result = ProcessedEvent(
                event=event,
                decision=decision,
                enrichment=enrichment,
                task_id=task_id,
                stale=stale,
            )
            await self._store.succeed(event.event_id, result)
            self._trace.emit(TraceEvent.now(trace_id, "pipeline", "succeeded", event.event_id))
            return result
        except Exception as exc:
            await self._store.fail(event.event_id, exc)
            self._trace.emit(TraceEvent.now(trace_id, "pipeline", "failed", event.event_id, type(exc).__name__))
            raise
