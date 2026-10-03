import json
from pathlib import Path

import pytest

from ai_reliability_lab.models import CareRequest, CaregiverProfile
from ai_reliability_lab.scoring import score_match


CASES = json.loads((Path(__file__).parent / "golden" / "matching_cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_matching_scores_are_golden_and_repeatable(case: dict) -> None:
    profile = CaregiverProfile.model_validate(case["profile"])
    request = CareRequest.model_validate(case["request"])

    first = score_match(profile, request)
    second = score_match(profile, request)

    assert first == second
    assert first.total == case["expected_total"]
