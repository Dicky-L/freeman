from __future__ import annotations

import asyncio
import os
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any, Protocol


class ProviderError(RuntimeError):
    pass


class TransientProviderError(ProviderError):
    pass


class LLMProvider(Protocol):
    name: str

    async def generate(self, prompt: str, json_schema: dict[str, Any]) -> str: ...


class FakeProvider:
    """Deterministic provider for tests. Outcomes may be strings or exceptions."""

    def __init__(self, name: str, outcomes: list[str | Exception]) -> None:
        self.name = name
        self._outcomes = deque(outcomes)
        self.calls = 0

    async def generate(self, prompt: str, json_schema: dict[str, Any]) -> str:
        del prompt, json_schema
        self.calls += 1
        if not self._outcomes:
            raise ProviderError(f"{self.name}: no fake outcome configured")
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FunctionProvider:
    """Adapter for an async function, useful when wrapping an existing ADK agent."""

    def __init__(
        self,
        name: str,
        fn: Callable[[str, dict[str, Any]], Awaitable[str]],
    ) -> None:
        self.name = name
        self._fn = fn

    async def generate(self, prompt: str, json_schema: dict[str, Any]) -> str:
        return await self._fn(prompt, json_schema)


class GeminiInteractionsProvider:
    """Optional Gemini adapter using Google's Interactions API."""

    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install with: pip install -e '.[gemini]'") from exc
        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self._model = model

    async def generate(self, prompt: str, json_schema: dict[str, Any]) -> str:
        def _call() -> str:
            interaction = self._client.interactions.create(
                model=self._model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": json_schema,
                },
            )
            return interaction.output_text

        try:
            return await asyncio.to_thread(_call)
        except Exception as exc:
            raise TransientProviderError(str(exc)) from exc
