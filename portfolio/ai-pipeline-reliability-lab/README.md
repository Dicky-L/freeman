# AI Pipeline Reliability Lab

A small, runnable portfolio project that demonstrates how I harden an existing LLM/data pipeline before launch.

The focus is deliberately **not** prompt cleverness. It is production reliability: schema enforcement, retries/fallbacks, async race prevention, deterministic business rules, observability, regression tests, and fresh derived data.

## Problems demonstrated

| Production failure mode | Pattern in this repo |
|---|---|
| LLM returns malformed or partial JSON | Pydantic/JSON Schema validation before data is accepted |
| Provider/network intermittently fails | Timeout + exponential retry + provider fallback |
| Async duplicate events race and overwrite data | Atomic idempotency claim; PostgreSQL production pattern included |
| LLM makes fixed scoring rules drift | Pure deterministic scoring function |
| Prompt/model changes silently change behavior | Golden-file regression tests |
| Logs say “failed” but cannot reconstruct what happened | Trace IDs + structured stage/provider/attempt events |
| Stored age becomes stale | Store DOB, derive age at query time |

## Architecture

```text
Inbound event / profile
        |
        v
 Idempotency claim  ---- duplicate ---> return existing result/status
        |
        v
 ReliableStructuredLLM
   | schema validation
   | timeout / retry
   | provider fallback
   | trace events
        |
        v
 Validated CaregiverProfile
        |
        +--> deterministic matching score
        +--> transactional persistence (PostgreSQL pattern)
```

## Quick start

```bash
cd portfolio/ai-pipeline-reliability-lab
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python examples/run_demo.py
```

The test suite uses a deterministic fake provider, so no API key is required.

## Optional Gemini adapter

```bash
pip install -e '.[dev,gemini]'
export GEMINI_API_KEY=...
```

The core pipeline is provider-agnostic on purpose. An existing Google ADK runner can be wrapped behind the same `LLMProvider` interface without rewriting validation/retry/scoring logic.

## Stabilisation order

1. Stop silent corruption first: idempotency + schema validation.
2. Make failure explicit: structured errors, retry policy, replay/manual-review path, trace IDs.
3. Remove LLMs from deterministic rules.
4. Add regression protection with golden datasets.
5. Only then migrate gateways/models/infrastructure.

## Scope note

This is a **portfolio demonstration**, not a claim that it is code from a previous client. It is intentionally compact so the reliability decisions are easy to review.
