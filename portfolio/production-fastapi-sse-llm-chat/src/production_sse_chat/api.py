from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse

from .config import Settings
from .logging_utils import configure_logging
from .models import ChatRequest
from .providers.base import ChatProvider
from .providers.demo import DemoProvider
from .providers.openai_provider import OpenAIResponsesProvider
from .service import ChatStreamService, StreamPolicy


ROOT = Path(__file__).resolve().parents[2]


def _build_provider(settings: Settings) -> ChatProvider:
    if settings.provider == "demo":
        return DemoProvider()
    if settings.provider == "openai":
        return OpenAIResponsesProvider(model=settings.openai_model)
    raise ValueError(f"unsupported LLM_PROVIDER={settings.provider!r}")


def create_app(
    *,
    provider: ChatProvider | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    configure_logging()
    settings = settings or Settings.from_env()
    provider = provider or _build_provider(settings)
    service = ChatStreamService(
        provider,
        StreamPolicy(
            idle_timeout_seconds=settings.stream_idle_timeout_seconds,
            max_duration_seconds=settings.stream_max_duration_seconds,
            heartbeat_seconds=settings.heartbeat_seconds,
            pre_token_retries=settings.pre_token_retries,
            retry_backoff_seconds=settings.retry_backoff_seconds,
        ),
    )

    app = FastAPI(title="Production FastAPI + SSE LLM Chat", version="0.1.0")

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready", "provider": provider.name}

    @app.get("/demo", include_in_schema=False)
    async def demo_page():
        return FileResponse(ROOT / "web" / "index.html")

    @app.post("/v1/chat/stream")
    async def stream_chat(payload: ChatRequest, request: Request) -> StreamingResponse:
        body = service.stream_sse(
            request_id=request.state.request_id,
            request=payload,
            disconnected=request.is_disconnected,
        )
        return StreamingResponse(
            body,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    return app


app = create_app()
