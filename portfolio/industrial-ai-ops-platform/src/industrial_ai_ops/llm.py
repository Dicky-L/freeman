from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol
from pydantic import ValidationError
from .models import AIEnrichment, IndustrialEvent


class LLMProvider(Protocol):
    name: str
    async def generate(self, prompt: str, json_schema: dict[str, Any]) -> str: ...


class FakeProvider:
    def __init__(self, name: str, outcomes: list[str | Exception]) -> None:
        self.name = name
        self._outcomes = deque(outcomes)
        self.calls = 0

    async def generate(self, prompt: str, json_schema: dict[str, Any]) -> str:
        del prompt, json_schema
        self.calls += 1
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@dataclass(frozen=True)
class RetryPolicy:
    attempts_per_provider: int = 2
    timeout_seconds: float = 10.0
    base_backoff_seconds: float = 0.05


class EnrichmentFailed(RuntimeError):
    pass


class StructuredAIEnricher:
    def __init__(self, providers: list[LLMProvider], retry: RetryPolicy | None = None) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self._providers = providers
        self._retry = retry or RetryPolicy()

    async def enrich(self, event: IndustrialEvent) -> AIEnrichment:
        schema = AIEnrichment.model_json_schema()
        prompt = (
            "Summarize this industrial event and suggest non-destructive operator checks. "
            "Return strict JSON only.\n" + event.model_dump_json()
        )
        errors: list[str] = []
        for provider in self._providers:
            for attempt in range(1, self._retry.attempts_per_provider + 1):
                try:
                    raw = await asyncio.wait_for(
                        provider.generate(prompt, schema),
                        timeout=self._retry.timeout_seconds,
                    )
                    return AIEnrichment.model_validate_json(raw)
                except (ValidationError, ValueError, asyncio.TimeoutError, RuntimeError) as exc:
                    errors.append(f"{provider.name}#{attempt}:{type(exc).__name__}")
                    if attempt < self._retry.attempts_per_provider:
                        await asyncio.sleep(self._retry.base_backoff_seconds * (2 ** (attempt - 1)))
        raise EnrichmentFailed(";".join(errors))
