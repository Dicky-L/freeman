from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from .observability import EventSink, NullEventSink, PipelineEvent
from .providers import LLMProvider

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class RetryPolicy:
    attempts_per_provider: int = 2
    timeout_seconds: float = 15.0
    base_backoff_seconds: float = 0.05


class StructuredOutputError(RuntimeError):
    pass


class FallbackExhausted(RuntimeError):
    pass


class ReliableStructuredLLM(Generic[T]):
    """Schema validation + timeout + retry + provider fallback + trace events."""

    def __init__(
        self,
        providers: list[LLMProvider],
        schema_model: type[T],
        *,
        retry: RetryPolicy | None = None,
        events: EventSink | None = None,
    ) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self._providers = providers
        self._schema_model = schema_model
        self._retry = retry or RetryPolicy()
        self._events = events or NullEventSink()

    async def generate(self, prompt: str, *, trace_id: str | None = None) -> T:
        trace_id = trace_id or uuid.uuid4().hex
        schema = self._schema_model.model_json_schema()
        errors: list[str] = []

        for provider in self._providers:
            for attempt in range(1, self._retry.attempts_per_provider + 1):
                started = time.perf_counter()
                try:
                    raw = await asyncio.wait_for(
                        provider.generate(prompt, schema),
                        timeout=self._retry.timeout_seconds,
                    )
                    value = self._schema_model.model_validate_json(raw)
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    self._events.emit(
                        PipelineEvent(
                            trace_id=trace_id,
                            stage="llm",
                            status="ok",
                            provider=provider.name,
                            attempt=attempt,
                            latency_ms=latency_ms,
                        )
                    )
                    return value
                except (ValidationError, ValueError) as exc:
                    error = StructuredOutputError(str(exc))
                except Exception as exc:
                    error = exc

                latency_ms = int((time.perf_counter() - started) * 1000)
                errors.append(f"{provider.name}#{attempt}: {type(error).__name__}: {error}")
                self._events.emit(
                    PipelineEvent(
                        trace_id=trace_id,
                        stage="llm",
                        status="retry" if attempt < self._retry.attempts_per_provider else "fallback",
                        provider=provider.name,
                        attempt=attempt,
                        latency_ms=latency_ms,
                        error_type=type(error).__name__,
                    )
                )
                if attempt < self._retry.attempts_per_provider:
                    await asyncio.sleep(self._retry.base_backoff_seconds * (2 ** (attempt - 1)))

        raise FallbackExhausted(" | ".join(errors))
