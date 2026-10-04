from datetime import datetime, timedelta, timezone
import pytest
from industrial_ai_ops.models import IndustrialEvent


@pytest.fixture
def event_factory():
    def _make(**overrides):
        now = datetime.now(timezone.utc)
        data = dict(
            event_id="evt-001",
            source="edge-gateway-01",
            equipment_id="press-line-3",
            metric="energy_deviation_pct",
            value=28.0,
            unit="%",
            event_time=now - timedelta(seconds=30),
            received_at=now,
            context={"site": "plant-a", "line": "L3"},
        )
        data.update(overrides)
        return IndustrialEvent(**data)
    return _make
