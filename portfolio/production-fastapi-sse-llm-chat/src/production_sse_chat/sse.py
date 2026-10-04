from __future__ import annotations

import json
from typing import Any


def encode_event(
    *,
    event: str,
    data: Any,
    event_id: str | None = None,
    retry_ms: int | None = None,
) -> bytes:
    """Encode one SSE frame.

    JSON is used for event payloads so text deltas containing newlines remain a
    single, unambiguous JSON value on the wire.
    """

    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    if retry_ms is not None:
        lines.append(f"retry: {retry_ms}")

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    return ("\n".join(lines) + "\n\n").encode("utf-8")


def encode_comment(comment: str = "ping") -> bytes:
    safe = comment.replace("\r", " ").replace("\n", " ")
    return f": {safe}\n\n".encode("utf-8")
