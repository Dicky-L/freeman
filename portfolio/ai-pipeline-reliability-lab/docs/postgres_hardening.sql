-- Production version of the in-memory idempotency pattern.
-- The UNIQUE key prevents duplicate external events from creating duplicate work.

CREATE TABLE pipeline_job (
  id BIGSERIAL PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
  payload JSONB NOT NULL,
  result JSONB,
  error JSONB,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX pipeline_job_status_created_idx
  ON pipeline_job(status, created_at);

-- Workers claim rows without racing each other.
-- Keep the transaction short; do not hold this lock during an LLM network call.
BEGIN;
SELECT id
FROM pipeline_job
WHERE status = 'pending'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1;
-- UPDATE the selected row to running + increment attempt_count here.
COMMIT;

-- In production, pair this with an outbox table when a DB mutation and
-- an external notification must be delivered atomically.
