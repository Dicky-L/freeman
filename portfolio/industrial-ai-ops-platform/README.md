[中文版](README.zh-CN.md)

# Industrial AI Operations Platform

A compact reference project for **industrial event processing + workflow integration + AI enrichment**.

This project is intentionally broader than a single LLM pipeline. It is based on engineering patterns I have worked with in enterprise/industrial systems: data ingestion, deterministic business rules, task/workflow integration, data freshness, auditability, retries, and operational diagnostics. AI is added as one capability inside the system rather than being allowed to control core business logic.

> This is a portfolio implementation built from reusable engineering patterns. It does not contain employer/client source code or private business data.

## What it does

```text
Industrial event / external webhook
              |
              v
      idempotent ingestion
              |
              v
       freshness validation
              |
              v
     deterministic rule engine
              |
      +-------+--------+
      |                |
      v                v
 persist/observe    AI enrichment
                    strict schema
                    retry/fallback
                         |
                         v
                workflow/task-center
                         |
                         v
                   audit / trace
```

## Capabilities

- FastAPI event ingestion and query endpoints
- Python async pipeline orchestration
- duplicate-event / webhook idempotency
- deterministic rule engine for severity and routing
- structured LLM output validation with Pydantic/JSON Schema
- timeout, retry, exponential backoff and provider fallback
- external task-center abstraction with idempotent callbacks
- data freshness calculated from timestamps rather than stored derived values
- stage-level trace/audit events
- PostgreSQL production schema and `FOR UPDATE SKIP LOCKED` worker pattern
- deterministic tests that do not require a real LLM API key

## Why rules and AI are separated

For industrial and enterprise systems, thresholds, approvals, routing and state transitions need to be repeatable and explainable. The LLM is used only for **unstructured enrichment** such as summaries, probable causes and suggested operator checks. Business severity and workflow decisions stay deterministic.

This also makes provider replacement much safer: Gemini/OpenAI/other providers can change without changing core business behavior.

## Quick start

```bash
cd portfolio/industrial-ai-ops-platform
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

Run API:

```bash
pip install uvicorn
uvicorn industrial_ai_ops.api:app --app-dir src --reload
```

Endpoints:

- `POST /events`
- `GET /events/{event_id}`
- `POST /tasks/callback`
- `GET /healthz`

## Failure modes covered

| Failure mode | Design response |
|---|---|
| duplicate webhook/event | atomic idempotency claim |
| stale telemetry | derive freshness from event timestamp |
| fixed rules drift because an LLM decides them | deterministic rule engine |
| malformed model JSON | schema validation before acceptance |
| model/provider outage | timeout + retry + fallback |
| duplicate workflow callback | callback idempotency key |
| difficult production diagnosis | trace ID + stage-level audit events |
| concurrent workers race on work | PostgreSQL `FOR UPDATE SKIP LOCKED` pattern |

## Where this can grow

- Redis/PostgreSQL-backed job repository
- outbox pattern for DB + external notification consistency
- dead-letter queue and controlled replay
- Langfuse/OpenTelemetry tracing
- configurable rules/prompts by tenant/site
- multi-provider LLM gateway
- Vue 3 operations console for trace, replay and workflow inspection
- Kubernetes/ArgoCD deployment

See [architecture notes](docs/architecture.md) and [PostgreSQL schema](docs/schema.sql).
