from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[str, Field(min_length=1, max_length=12_000)]
    system: Annotated[str | None, Field(max_length=4_000)] = None
    conversation_id: Annotated[str | None, Field(max_length=128)] = None
