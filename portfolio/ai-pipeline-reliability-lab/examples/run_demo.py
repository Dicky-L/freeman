import asyncio

from ai_reliability_lab.models import CaregiverProfile
from ai_reliability_lab.observability import JsonLineEventSink
from ai_reliability_lab.pipeline import InMemoryJobStore, ProfilePipeline
from ai_reliability_lab.providers import FakeProvider
from ai_reliability_lab.reliable_llm import ReliableStructuredLLM, RetryPolicy


async def main() -> None:
    provider = FakeProvider(
        "gemini-simulated",
        [
            "not-json",
            '{"caregiver_id":"cg-42","full_name":"Demo User","date_of_birth":"1988-07-11",'
            '"languages":["English"],"skills":["eldercare"],"years_experience":7,'
            '"availability_hours_per_week":35,"summary":"Validated after retry"}',
        ],
    )
    events = JsonLineEventSink()
    llm = ReliableStructuredLLM(
        [provider],
        CaregiverProfile,
        retry=RetryPolicy(attempts_per_provider=2, base_backoff_seconds=0),
        events=events,
    )
    pipeline = ProfilePipeline(llm, InMemoryJobStore(), events=events)
    profile = await pipeline.process("demo-message-1", "unstructured caregiver profile")
    print(profile.model_dump_json(indent=2) if profile else "already in progress")


if __name__ == "__main__":
    asyncio.run(main())
