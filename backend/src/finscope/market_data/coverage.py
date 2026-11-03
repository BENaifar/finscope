from collections.abc import Iterable
from datetime import date


def find_missing_dates(
    expected: Iterable[date], stored: Iterable[date]
) -> tuple[date, ...]:
    """Return expected dates that are not stored, ascending and without repeats.

    Stored dates that are not expected are ignored: they neither hide a gap nor
    count as one.
    """
    return tuple(sorted(set(expected) - set(stored)))
