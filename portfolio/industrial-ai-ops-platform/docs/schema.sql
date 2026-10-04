CREATE TABLE industrial_event (
  event_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  equipment_id TEXT NOT NULL,
  event_time TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL,
  result JSONB,
  error JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workflow_callback (
  callback_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_event (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  detail JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT event_id
FROM industrial_event
WHERE status = 'received'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1;
