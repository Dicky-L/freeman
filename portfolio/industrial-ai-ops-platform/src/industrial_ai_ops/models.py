from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(StrEnum):
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IndustrialEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    equipment_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: float
    unit: str = ""
    event_time: datetime
    received_at: datetime
    context: dict[str, str | int | float | bool] = Field(default_factory=dict)


class RuleDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Severity
    reason_codes: list[str]
    requires_ai_enrichment: bool
    requires_workflow_task: bool


class AIEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=500)
    probable_causes: list[str] = Field(default_factory=list, max_length=5)
    recommended_actions: list[str] = Field(default_factory=list, max_length=5)
    confidence: Annotated[float, Field(ge=0, le=1)]


class ProcessedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: IndustrialEvent
    decision: RuleDecision
    enrichment: AIEnrichment | None = None
    task_id: str | None = None
    stale: bool = False


class TaskCallback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    callback_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    operator: str | None = None
    note: str | None = None
