from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from ..models import ChatRequest


class DemoProvider:
    """No-key provider for local demos and CI."""

    name = "demo"

    def __init__(self, delay_seconds: float = 0.02) -> None:
        self.delay_seconds = delay_seconds

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        answer = (
            "Demo stream. In production set LLM_PROVIDER=openai. "
            f"You said: {request.message}"
        )
        for token in answer.split(" "):
            await asyncio.sleep(self.delay_seconds)
            yield token + " "
