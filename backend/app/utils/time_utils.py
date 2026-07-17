from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc
WIB = timezone(timedelta(hours=7), "WIB")


def utc_now() -> datetime:
    """Return naive UTC for SQLite compatibility and existing comparisons."""
    return datetime.utcnow()


def to_wib(value: datetime) -> datetime:
    """Convert stored timestamps to WIB.

    Existing SQLite records are naive UTC because the project used datetime.utcnow().
    Treat naive values as UTC, then convert to Asia/Jakarta (+07:00).
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(WIB)


def to_wib_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return to_wib(value).isoformat()


def now_wib_iso() -> str:
    return datetime.now(WIB).isoformat()
