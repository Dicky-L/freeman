from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from ..models import ChatRequest


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, code: str = "upstream_error", retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ChatProvider(Protocol):
    name: str

    def stream(self, request: ChatRequest) -> AsyncIterator[str]: ...
