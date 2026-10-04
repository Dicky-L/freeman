import asyncio

import pytest

from production_sse_chat.models import ChatRequest
from production_sse_chat.service import ChatStreamService, StreamPolicy

from helpers import ScriptedProvider, collect, never_disconnected


def service(provider, **overrides) -> ChatStreamService:
    defaults = dict(
        idle_timeout_seconds=0.2,
        max_duration_seconds=2,
        heartbeat_seconds=0.02,
        pre_token_retries=1,
        retry_backoff_seconds=0.001,
    )
    defaults.update(overrides)
    return ChatStreamService(provider, StreamPolicy(**defaults))


@pytest.mark.asyncio
async def test_transient_failure_retries_before_first_delta() -> None:
    provider = ScriptedProvider(["hello"], fail_first_calls=1)
    body = await collect(
        service(provider).stream_sse(
            request_id="r1",
            request=ChatRequest(message="hi"),
            disconnected=never_disconnected,
        )
    )
    assert provider.calls == 2
    assert 'event: delta' in body
    assert '"text":"hello"' in body
    assert '"attempts":2' in body
    assert 'event: error' not in body


@pytest.mark.asyncio
async def test_partial_output_is_not_transparently_retried() -> None:
    provider = ScriptedProvider(["hello", "world"], fail_after_chunks=1)
    body = await collect(
        service(provider, pre_token_retries=5).stream_sse(
            request_id="r2",
            request=ChatRequest(message="hi"),
            disconnected=never_disconnected,
        )
    )
    assert provider.calls == 1
    assert '"text":"hello"' in body
    assert 'event: error' in body
    assert '"code":"partial"' in body


@pytest.mark.asyncio
async def test_heartbeat_is_emitted_while_waiting_for_provider() -> None:
    provider = ScriptedProvider(["slow"], delay_seconds=0.05)
    body = await collect(
        service(provider, heartbeat_seconds=0.01, idle_timeout_seconds=0.2).stream_sse(
            request_id="r3",
            request=ChatRequest(message="hi"),
            disconnected=never_disconnected,
        )
    )
    assert ': ping\n\n' in body
    assert '"text":"slow"' in body


@pytest.mark.asyncio
async def test_idle_timeout_returns_retryable_error_after_retries_exhausted() -> None:
    provider = ScriptedProvider(["too-late"], delay_seconds=0.1)
    body = await collect(
        service(
            provider,
            heartbeat_seconds=0.005,
            idle_timeout_seconds=0.02,
            pre_token_retries=1,
        ).stream_sse(
            request_id="r4",
            request=ChatRequest(message="hi"),
            disconnected=never_disconnected,
        )
    )
    assert provider.calls == 2
    assert 'event: error' in body
    assert '"code":"upstream_idle_timeout"' in body
    assert '"retryable":true' in body


@pytest.mark.asyncio
async def test_cancellation_closes_provider_stream() -> None:
    provider = ScriptedProvider(["later"], delay_seconds=1)
    stream = service(provider, heartbeat_seconds=1, idle_timeout_seconds=5).stream_sse(
        request_id="r5",
        request=ChatRequest(message="hi"),
        disconnected=never_disconnected,
    )

    first = await anext(stream)
    assert b"event: meta" in first

    task = asyncio.create_task(anext(stream))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert provider.closed == 1
