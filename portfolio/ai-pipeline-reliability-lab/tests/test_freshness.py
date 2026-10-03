from datetime import date

import pytest

from ai_reliability_lab.freshness import age_on


def test_age_is_calculated_at_query_time() -> None:
    dob = date(1990, 10, 5)
    assert age_on(dob, date(2026, 10, 4)) == 35
    assert age_on(dob, date(2026, 10, 5)) == 36


def test_future_dob_is_rejected() -> None:
    with pytest.raises(ValueError):
        age_on(date(2030, 1, 1), date(2026, 1, 1))
