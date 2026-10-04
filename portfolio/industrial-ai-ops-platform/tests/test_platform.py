import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from industrial_ai_ops.api import app
from industrial_ai_ops.freshness import is_stale
from industrial_ai_ops.llm import FakeProvider, RetryPolicy, StructuredAIEnricher
from industrial_ai_ops.models import RuleDecision, Severity, TaskCallback
from industrial_ai_ops.observability import ListTraceSink
from industrial_ai_ops.pipeline import IndustrialAIPipeline
from industrial_ai_ops.rules import evaluate_rules
from industrial_ai_ops.store import InMemoryEventStore
from industrial_ai_ops.workflow import InMemoryTaskCenter

VALID = '{"summary":"Investigate deviation","probable_causes":["load change"],"recommended_actions":["compare upstream load"],"confidence":0.81}'


def test_deterministic_rule_engine(event_factory):
    event = event_factory(value=36.0)
    assert evaluate_rules(event) == evaluate_rules(event)
    assert evaluate_rules(event).severity == Severity.CRITICAL


def test_freshness_is_derived():
    now = datetime.now(timezone.utc)
    assert is_stale(now - timedelta(seconds=10), now, 60) is False
    assert is_stale(now - timedelta(seconds=61), now, 60) is True


@pytest.mark.asyncio
async def test_invalid_output_retries(event_factory):
    provider = FakeProvider("primary", ["not-json", VALID])
    enricher = StructuredAIEnricher([provider], RetryPolicy(attempts_per_provider=2, base_backoff_seconds=0))
    assert (await enricher.enrich(event_factory())).confidence == 0.81
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_provider_fallback(event_factory):
    primary = FakeProvider("primary", [RuntimeError("503"), RuntimeError("503")])
    secondary = FakeProvider("secondary", [VALID])
    enricher = StructuredAIEnricher([primary, secondary], RetryPolicy(attempts_per_provider=2, base_backoff_seconds=0))
    assert (await enricher.enrich(event_factory())).summary == "Investigate deviation"
    assert primary.calls == 2 and secondary.calls == 1


@pytest.mark.asyncio
async def test_duplicate_events_are_idempotent(event_factory):
    provider = FakeProvider("primary", [VALID])
    pipeline = IndustrialAIPipeline(
        InMemoryEventStore(),
        InMemoryTaskCenter(),
        StructuredAIEnricher([provider], RetryPolicy(base_backoff_seconds=0)),
    )
    event = event_factory(value=30)
    await asyncio.gather(*[pipeline.process(event) for _ in range(8)])
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_high_event_creates_task_and_trace(event_factory):
    traces = ListTraceSink()
    pipeline = IndustrialAIPipeline(
        InMemoryEventStore(),
        InMemoryTaskCenter(),
        StructuredAIEnricher([FakeProvider("primary", [VALID])], RetryPolicy(base_backoff_seconds=0)),
        trace_sink=traces,
    )
    result = await pipeline.process(event_factory(value=28))
    assert result and result.task_id
    assert {e.stage for e in traces.events} >= {"ingest", "rules", "ai", "workflow", "pipeline"}


@pytest.mark.asyncio
async def test_task_callback_is_idempotent(event_factory):
    center = InMemoryTaskCenter()
    task = await center.create_task(
        event_factory(),
        RuleDecision(
            severity=Severity.HIGH,
            reason_codes=["THRESHOLD_HIGH"],
            requires_ai_enrichment=True,
            requires_workflow_task=True,
        ),
    )
    callback = TaskCallback(callback_id="cb-001", task_id=task.task_id, status="approved")
    assert await center.apply_callback(callback) is True
    assert await center.apply_callback(callback) is False


def test_health_endpoint():
    client = TestClient(app)
    assert client.get("/healthz").json() == {"status": "ok"}
