from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from production_sse_chat.models import ChatRequest
from production_sse_chat.providers.base import ProviderError


class ScriptedProvider:
    name = "scripted"

    def __init__(
        self,
        chunks: list[str],
        *,
        delay_seconds: float = 0,
        fail_first_calls: int = 0,
        fail_after_chunks: int | None = None,
        retryable: bool = True,
    ) -> None:
        self.chunks = chunks
        self.delay_seconds = delay_seconds
        self.fail_first_calls = fail_first_calls
        self.fail_after_chunks = fail_after_chunks
        self.retryable = retryable
        self.calls = 0
        self.closed = 0

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        del request
        self.calls += 1
        call = self.calls
        try:
            if call <= self.fail_first_calls:
                raise ProviderError("planned pre-token failure", code="planned", retryable=self.retryable)
            for index, chunk in enumerate(self.chunks):
                if self.delay_seconds:
                    await asyncio.sleep(self.delay_seconds)
                if self.fail_after_chunks is not None and index >= self.fail_after_chunks:
                    raise ProviderError("planned partial failure", code="partial", retryable=self.retryable)
                yield chunk
            if self.fail_after_chunks is not None and self.fail_after_chunks >= len(self.chunks):
                raise ProviderError("planned end failure", code="partial", retryable=self.retryable)
        finally:
            self.closed += 1


async def never_disconnected() -> bool:
    return False


async def collect(stream) -> str:
    chunks: list[bytes] = []
    async for chunk in stream:
        chunks.append(chunk)
    return b"".join(chunks).decode("utf-8")
