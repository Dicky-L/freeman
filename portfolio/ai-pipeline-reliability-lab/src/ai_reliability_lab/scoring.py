from __future__ import annotations

from .models import CareRequest, CaregiverProfile, MatchScore


def _norm(values: list[str]) -> set[str]:
    return {value.strip().casefold() for value in values if value.strip()}


def _coverage(actual: set[str], required: set[str]) -> float:
    if not required:
        return 1.0
    return len(actual & required) / len(required)


def score_match(profile: CaregiverProfile, request: CareRequest) -> MatchScore:
    """Pure deterministic scoring: no LLM in fixed business rules."""

    languages = _norm(profile.languages)
    required_languages = _norm(request.required_languages)
    skills = _norm(profile.skills)
    required_skills = _norm(request.required_skills)

    language_score = 40 * _coverage(languages, required_languages)
    skill_score = 35 * _coverage(skills, required_skills)

    if request.min_years_experience == 0:
        experience_score = 15.0
    else:
        experience_score = 15 * min(
            profile.years_experience / request.min_years_experience,
            1.0,
        )

    if request.min_hours_per_week == 0:
        availability_score = 10.0
    else:
        availability_score = 10 * min(
            profile.availability_hours_per_week / request.min_hours_per_week,
            1.0,
        )

    missing: list[str] = []
    missing.extend(f"language:{item}" for item in sorted(required_languages - languages))
    missing.extend(f"skill:{item}" for item in sorted(required_skills - skills))
    if profile.years_experience < request.min_years_experience:
        missing.append("experience")
    if profile.availability_hours_per_week < request.min_hours_per_week:
        missing.append("availability")

    return MatchScore(
        total=round(language_score + skill_score + experience_score + availability_score, 2),
        language_score=round(language_score, 2),
        skill_score=round(skill_score, 2),
        experience_score=round(experience_score, 2),
        availability_score=round(availability_score, 2),
        missing_requirements=missing,
    )
