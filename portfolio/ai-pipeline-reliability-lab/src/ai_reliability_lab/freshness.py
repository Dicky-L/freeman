from datetime import date


def age_on(date_of_birth: date, on_date: date) -> int:
    """Calculate age from DOB at query time instead of storing a stale age."""

    if date_of_birth > on_date:
        raise ValueError("date_of_birth cannot be in the future")
    birthday_passed = (on_date.month, on_date.day) >= (
        date_of_birth.month,
        date_of_birth.day,
    )
    return on_date.year - date_of_birth.year - (0 if birthday_passed else 1)
