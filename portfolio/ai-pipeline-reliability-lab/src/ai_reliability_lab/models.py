from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CaregiverProfile(BaseModel):
    """Validated profile produced by the enrichment pipeline."""

    model_config = ConfigDict(extra="forbid")

    caregiver_id: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    date_of_birth: date
    languages: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    years_experience: Annotated[int, Field(ge=0, le=80)] = 0
    availability_hours_per_week: Annotated[int, Field(ge=0, le=168)] = 0
    summary: str = ""


class CareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_languages: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    min_years_experience: Annotated[int, Field(ge=0, le=80)] = 0
    min_hours_per_week: Annotated[int, Field(ge=0, le=168)] = 0


class MatchScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: Annotated[float, Field(ge=0, le=100)]
    language_score: float
    skill_score: float
    experience_score: float
    availability_score: float
    missing_requirements: list[str] = Field(default_factory=list)
