from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from ..models import ChatRequest
from .base import ProviderError


class OpenAIResponsesProvider:
    """OpenAI Responses API streaming adapter."""

    name = "openai"

    def __init__(self, model: str) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("Install with: pip install -e '.[openai]'") from exc
        self._client = AsyncOpenAI()
        self._model = model

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        try:
            from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

            input_items: list[dict[str, str]] = []
            if request.system:
                input_items.append({"role": "developer", "content": request.system})
            input_items.append({"role": "user", "content": request.message})

            async with self._client.responses.stream(
                model=self._model,
                input=input_items,
            ) as stream:
                async for event in stream:
                    if event.type == "response.output_text.delta" and event.delta:
                        yield event.delta
        except asyncio.CancelledError:
            raise
        except RateLimitError as exc:
            raise ProviderError(str(exc), code="rate_limited", retryable=True) from exc
        except APITimeoutError as exc:
            raise ProviderError(str(exc), code="provider_timeout", retryable=True) from exc
        except APIConnectionError as exc:
            raise ProviderError(str(exc), code="provider_connection", retryable=True) from exc
        except APIStatusError as exc:
            retryable = exc.status_code == 429 or exc.status_code >= 500
            raise ProviderError(
                str(exc),
                code=f"provider_http_{exc.status_code}",
                retryable=retryable,
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(str(exc), code="provider_unexpected", retryable=False) from exc
