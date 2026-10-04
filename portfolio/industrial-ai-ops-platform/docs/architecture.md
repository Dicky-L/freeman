# Architecture notes

This demo is derived from patterns common in industrial internet / energy-management systems: edge/cloud event ingestion, deterministic business rules, external workflow/task-center integration, freshness checks, auditability, and fault isolation.

```text
Edge / external system
        |
        v
  REST / webhook ingest
        |
        v
 idempotency boundary ------ duplicate ------> existing state/result
        |
        v
 data freshness check
        |
        v
 deterministic rule engine
        |
        +-------------------- info -----------> persist / observe
        |
        v
 optional AI enrichment
  schema validation
  timeout / retry
  provider fallback
        |
        v
 workflow/task-center integration
        |
        v
 audit / trace / replay-ready state
```

## Engineering boundaries

- Rules decide business severity. LLMs do not own fixed thresholds or workflow state transitions.
- LLM output is untrusted external input until schema validation succeeds.
- Every external event/callback has an idempotency boundary.
- Freshness is derived from timestamps, not persisted as an aging value.
- Audit data is part of the product so failures can be diagnosed and replayed.
