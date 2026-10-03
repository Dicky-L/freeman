import asyncio

import pytest

from ai_reliability_lab.models import CaregiverProfile
from ai_reliability_lab.pipeline import InMemoryJobStore, JobStatus, ProfilePipeline
from ai_reliability_lab.providers import FakeProvider
from ai_reliability_lab.reliable_llm import ReliableStructuredLLM, RetryPolicy


VALID = """{
  "caregiver_id": "cg-9",
  "full_name": "Mei Lim",
  "date_of_birth": "1990-08-20",
  "languages": ["English"],
  "skills": ["eldercare"],
  "years_experience": 5,
  "availability_hours_per_week": 30,
  "summary": "Caregiver"
}"""


@pytest.mark.asyncio
async def test_concurrent_duplicate_jobs_are_processed_once() -> None:
    provider = FakeProvider("primary", [VALID])
    llm = ReliableStructuredLLM(
        [provider],
        CaregiverProfile,
        retry=RetryPolicy(base_backoff_seconds=0),
    )
    store = InMemoryJobStore()
    pipeline = ProfilePipeline(llm, store)

    results = await asyncio.gather(
        *[pipeline.process("wa-msg-123", "same inbound message") for _ in range(8)]
    )

    stored = await store.get("wa-msg-123")
    assert provider.calls == 1
    assert stored is not None and stored.status == JobStatus.SUCCEEDED
    assert sum(result is not None for result in results) >= 1
