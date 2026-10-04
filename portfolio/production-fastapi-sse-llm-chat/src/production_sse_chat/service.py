from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass

from .logging_utils import log_event
from .models import ChatRequest
from .providers.base import ChatProvider, ProviderError
from .sse import encode_comment, encode_event

DisconnectChecker = Callable[[], Awaitable[bool]]


@dataclass(frozen=True)
class StreamPolicy:
    idle_timeout_seconds: float = 30.0
    max_duration_seconds: float = 300.0
    heartbeat_seconds: float = 10.0
    pre_token_retries: int = 1
    retry_backoff_seconds: float = 0.25


class UpstreamIdleTimeout(TimeoutError):
    pass


class StreamDeadlineExceeded(TimeoutError):
    pass


async def _close_stream(stream: AsyncIterator[str] | None) -> None:
    if stream is None:
        return
    aclose = getattr(stream, "aclose", None)
    if aclose is not None:
        with suppress(Exception):
            await aclose()


class ChatStreamService:
    def __init__(self, provider: ChatProvider, policy: StreamPolicy) -> None:
        self.provider = provider
        self.policy = policy

    async def stream_sse(
        self,
        *,
        request_id: str,
        request: ChatRequest,
        disconnected: DisconnectChecker,
    ) -> AsyncIterator[bytes]:
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        deadline = started_at + self.policy.max_duration_seconds
        seq = 0
        sent_delta = False
        attempt = 0

        yield encode_event(
            event="meta",
            event_id=str(seq),
            retry_ms=3000,
            data={"request_id": request_id, "provider": self.provider.name},
        )
        seq += 1
        log_event("stream_started", request_id=request_id, provider=self.provider.name)

        while True:
            attempt += 1
            provider_stream: AsyncIterator[str] | None = None
            next_task: asyncio.Task[str] | None = None
            last_delta_at = loop.time()
            try:
                provider_stream = self.provider.stream(request)
                next_task = asyncio.create_task(anext(provider_stream))

                while True:
                    if await disconnected():
                        log_event(
                            "client_disconnected",
                            request_id=request_id,
                            provider=self.provider.name,
                            attempt=attempt,
                        )
                        return

                    now = loop.time()
                    if now >= deadline:
                        raise StreamDeadlineExceeded("stream maximum duration exceeded")
                    if now - last_delta_at >= self.policy.idle_timeout_seconds:
                        raise UpstreamIdleTimeout("upstream produced no token before idle timeout")

                    wait_for = min(
                        self.policy.heartbeat_seconds,
                        deadline - now,
                        self.policy.idle_timeout_seconds - (now - last_delta_at),
                    )
                    done, _ = await asyncio.wait({next_task}, timeout=max(wait_for, 0.001))

                    if not done:
                        yield encode_comment("ping")
                        continue

                    try:
                        chunk = next_task.result()
                    except StopAsyncIteration:
                        yield encode_event(
                            event="done",
                            event_id=str(seq),
                            data={"request_id": request_id, "attempts": attempt},
                        )
                        log_event(
                            "stream_completed",
                            request_id=request_id,
                            provider=self.provider.name,
                            attempt=attempt,
                            duration_ms=int((loop.time() - started_at) * 1000),
                        )
                        return

                    if chunk:
                        sent_delta = True
                        last_delta_at = loop.time()
                        yield encode_event(
                            event="delta",
                            event_id=str(seq),
                            data={"text": chunk},
                        )
                        seq += 1

                    next_task = asyncio.create_task(anext(provider_stream))

            except asyncio.CancelledError:
                log_event(
                    "stream_cancelled",
                    request_id=request_id,
                    provider=self.provider.name,
                    attempt=attempt,
                )
                raise
            except (UpstreamIdleTimeout, StreamDeadlineExceeded) as exc:
                code = (
                    "upstream_idle_timeout"
                    if isinstance(exc, UpstreamIdleTimeout)
                    else "stream_deadline_exceeded"
                )
                retryable = isinstance(exc, UpstreamIdleTimeout)
                log_event(
                    "stream_error",
                    request_id=request_id,
                    provider=self.provider.name,
                    attempt=attempt,
                    code=code,
                    sent_delta=sent_delta,
                )
                if (
                    isinstance(exc, UpstreamIdleTimeout)
                    and not sent_delta
                    and attempt <= self.policy.pre_token_retries
                ):
                    await asyncio.sleep(self.policy.retry_backoff_seconds * attempt)
                    continue
                yield encode_event(
                    event="error",
                    event_id=str(seq),
                    data={"request_id": request_id, "code": code, "retryable": retryable},
                )
                return
            except ProviderError as exc:
                log_event(
                    "stream_error",
                    request_id=request_id,
                    provider=self.provider.name,
                    attempt=attempt,
                    code=exc.code,
                    sent_delta=sent_delta,
                    retryable=exc.retryable,
                )
                if (
                    not sent_delta
                    and exc.retryable
                    and attempt <= self.policy.pre_token_retries
                ):
                    await asyncio.sleep(self.policy.retry_backoff_seconds * attempt)
                    continue
                yield encode_event(
                    event="error",
                    event_id=str(seq),
                    data={"request_id": request_id, "code": exc.code, "retryable": exc.retryable},
                )
                return
            except Exception as exc:
                log_event(
                    "stream_error",
                    request_id=request_id,
                    provider=self.provider.name,
                    attempt=attempt,
                    code="internal_stream_error",
                    sent_delta=sent_delta,
                    error_type=type(exc).__name__,
                )
                yield encode_event(
                    event="error",
                    event_id=str(seq),
                    data={
                        "request_id": request_id,
                        "code": "internal_stream_error",
                        "retryable": False,
                    },
                )
                return
            finally:
                if next_task is not None and not next_task.done():
                    next_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await next_task
                await _close_stream(provider_stream)
