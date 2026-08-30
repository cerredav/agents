"""Current date, time, timezone, and location context."""

from __future__ import annotations

import os
from datetime import datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_current_datetime_context(
    *,
    location: str | None = None,
    timezone: str | tzinfo | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return deterministic temporal context and an explicitly sourced location.

    ``location`` takes precedence over ``AGENT_LOCATION``. Pass an IANA timezone
    such as ``America/New_York`` when relative dates must use a known locality.
    The optional ``now`` argument supports deterministic tests.
    """
    resolved_timezone = _resolve_timezone(timezone)
    current = now or datetime.now(tz=resolved_timezone)
    if current.tzinfo is None:
        current = current.replace(tzinfo=resolved_timezone)
    elif timezone is not None:
        current = current.astimezone(resolved_timezone)

    timezone_name = getattr(current.tzinfo, "key", None) or current.tzname()
    resolved_location = location or os.getenv("AGENT_LOCATION", None)

    context = {
        "current_date": current.date().isoformat(),
        "current_time": current.timetz().isoformat(timespec="seconds"),
        "current_datetime": current.isoformat(timespec="seconds"),
        "timezone": timezone_name,
        "utc_offset": current.strftime("%z"),
    }

    if resolved_location: context['location'] = resolved_location

    return context


def _resolve_timezone(timezone: str | tzinfo | None) -> tzinfo:
    if timezone is None:
        return datetime.now().astimezone().tzinfo or ZoneInfo("UTC")
    if isinstance(timezone, str):
        try:
            return ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"Unknown IANA timezone: {timezone}") from error
    if isinstance(timezone, tzinfo):
        return timezone
    raise TypeError("timezone must be an IANA timezone name or tzinfo instance.")
