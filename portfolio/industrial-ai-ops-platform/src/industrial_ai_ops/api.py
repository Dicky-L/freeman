from fastapi import FastAPI, HTTPException
from .llm import FakeProvider, RetryPolicy, StructuredAIEnricher
from .models import IndustrialEvent, TaskCallback
from .pipeline import IndustrialAIPipeline
from .store import InMemoryEventStore
from .workflow import InMemoryTaskCenter

VALID = (
    '{"summary":"Event requires operator review","probable_causes":["process deviation"],'
    '"recommended_actions":["verify sensor and process state"],"confidence":0.8}'
)

store = InMemoryEventStore()
tasks = InMemoryTaskCenter()
enricher = StructuredAIEnricher(
    [FakeProvider("demo-provider", [VALID] * 100)],
    RetryPolicy(base_backoff_seconds=0),
)
pipeline = IndustrialAIPipeline(store, tasks, enricher)
app = FastAPI(title="Industrial AI Operations Platform", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events")
async def ingest_event(event: IndustrialEvent):
    result = await pipeline.process(event)
    return result or {"status": "already-processing"}


@app.get("/events/{event_id}")
async def get_event(event_id: str):
    record = await store.get(event_id)
    if record is None:
        raise HTTPException(404, "event not found")
    return record


@app.post("/tasks/callback")
async def task_callback(callback: TaskCallback):
    try:
        applied = await tasks.apply_callback(callback)
    except KeyError:
        raise HTTPException(404, "task not found")
    return {"applied": applied}
