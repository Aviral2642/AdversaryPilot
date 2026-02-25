"""Timestamp utilities for AdversaryPilot."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time with timezone awareness.

    All timestamps in AdversaryPilot models should use this function
    instead of datetime.now() to ensure proper timezone handling.

    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)
