from datetime import datetime


def data_age_seconds(event_time: datetime, now: datetime) -> float:
    if event_time.tzinfo is None or now.tzinfo is None:
        raise ValueError("timezone-aware timestamps are required")
    return max(0.0, (now - event_time).total_seconds())


def is_stale(event_time: datetime, now: datetime, ttl_seconds: int) -> bool:
    return data_age_seconds(event_time, now) > ttl_seconds
