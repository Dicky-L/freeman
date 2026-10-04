from fastapi.testclient import TestClient

from production_sse_chat.api import create_app
from production_sse_chat.config import Settings

from helpers import ScriptedProvider


def test_stream_endpoint_and_request_id_header() -> None:
    provider = ScriptedProvider(["A", "B"])
    app = create_app(
        provider=provider,
        settings=Settings(
            provider="demo",
            stream_idle_timeout_seconds=1,
            stream_max_duration_seconds=5,
            heartbeat_seconds=0.1,
            pre_token_retries=0,
            retry_backoff_seconds=0.01,
        ),
    )
    client = TestClient(app)

    with client.stream(
        "POST",
        "/v1/chat/stream",
        headers={"X-Request-ID": "client-123"},
        json={"message": "hello"},
    ) as response:
        text = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-request-id"] == "client-123"
    assert response.headers["x-accel-buffering"] == "no"
    assert text.count("event: delta") == 2
    assert "event: done" in text
