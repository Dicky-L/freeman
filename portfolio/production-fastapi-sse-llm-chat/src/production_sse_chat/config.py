from __future__ import annotations

import os
from dataclasses import dataclass


def _float_env(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def _int_env(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


@dataclass(frozen=True)
class Settings:
    provider: str = "demo"
    openai_model: str = "gpt-5"
    stream_idle_timeout_seconds: float = 30.0
    stream_max_duration_seconds: float = 300.0
    heartbeat_seconds: float = 10.0
    pre_token_retries: int = 1
    retry_backoff_seconds: float = 0.25

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            provider=os.getenv("LLM_PROVIDER", "demo").strip().lower(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5").strip(),
            stream_idle_timeout_seconds=_float_env("STREAM_IDLE_TIMEOUT_SECONDS", 30.0),
            stream_max_duration_seconds=_float_env("STREAM_MAX_DURATION_SECONDS", 300.0),
            heartbeat_seconds=_float_env("SSE_HEARTBEAT_SECONDS", 10.0),
            pre_token_retries=_int_env("PRE_TOKEN_RETRIES", 1),
            retry_backoff_seconds=_float_env("RETRY_BACKOFF_SECONDS", 0.25),
        )
