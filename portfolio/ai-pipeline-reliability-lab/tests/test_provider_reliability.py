import pytest

from ai_reliability_lab.models import CaregiverProfile
from ai_reliability_lab.observability import ListEventSink
from ai_reliability_lab.providers import FakeProvider, TransientProviderError
from ai_reliability_lab.reliable_llm import ReliableStructuredLLM, RetryPolicy


VALID = """{
  "caregiver_id": "cg-1",
  "full_name": "Ana Tan",
  "date_of_birth": "1986-02-14",
  "languages": ["English", "Mandarin"],
  "skills": ["dementia", "mobility"],
  "years_experience": 8,
  "availability_hours_per_week": 40,
  "summary": "Experienced home caregiver"
}"""


@pytest.mark.asyncio
async def test_invalid_json_is_retried_then_validated() -> None:
    provider = FakeProvider("primary", ["not-json", VALID])
    events = ListEventSink()
    llm = ReliableStructuredLLM(
        [provider],
        CaregiverProfile,
        retry=RetryPolicy(attempts_per_provider=2, base_backoff_seconds=0),
        events=events,
    )

    result = await llm.generate("profile")

    assert result.caregiver_id == "cg-1"
    assert provider.calls == 2
    assert [event.status for event in events.events] == ["retry", "ok"]


@pytest.mark.asyncio
async def test_provider_failure_falls_back_to_secondary() -> None:
    primary = FakeProvider(
        "primary",
        [TransientProviderError("503"), TransientProviderError("503")],
    )
    secondary = FakeProvider("secondary", [VALID])
    llm = ReliableStructuredLLM(
        [primary, secondary],
        CaregiverProfile,
        retry=RetryPolicy(attempts_per_provider=2, base_backoff_seconds=0),
    )

    result = await llm.generate("profile")

    assert result.full_name == "Ana Tan"
    assert primary.calls == 2
    assert secondary.calls == 1
