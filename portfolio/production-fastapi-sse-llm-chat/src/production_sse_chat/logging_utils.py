from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


LOGGER_NAME = "production_sse_chat"


def configure_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


def log_event(event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **fields,
    }
    logging.getLogger(LOGGER_NAME).info(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    )
