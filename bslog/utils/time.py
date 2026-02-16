"""Time parsing and formatting utilities for bslog."""

import re
from datetime import UTC, datetime, timedelta


def parse_time_string(time_str: str) -> datetime:
    now = datetime.now(tz=UTC)

    # Check for relative time formats (1h, 30m, 2d, etc.)
    relative_match = re.match(r"^(\d+)([hdmw])$", time_str)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)

        if unit == "h":
            return now - timedelta(hours=amount)
        elif unit == "d":
            return now - timedelta(days=amount)
        elif unit == "m":
            return now - timedelta(minutes=amount)
        elif unit == "w":
            return now - timedelta(weeks=amount)
        else:
            raise ValueError(f"Unknown time unit: {unit}")

    # Check if it matches the pattern but with invalid unit
    if re.match(r"^\d+[a-zA-Z]$", time_str):
        unit = re.search(r"[a-zA-Z]$", time_str)
        raise ValueError(f"Unknown time unit: {unit.group(0) if unit else time_str}")

    # Try to parse as ISO date or other standard formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(time_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            continue

    raise ValueError(f"Invalid time format: {time_str}")


def format_date_time(date: datetime) -> str:
    utc_date = date.astimezone(UTC)
    return utc_date.strftime("%Y-%m-%d %H:%M:%S.") + f"{utc_date.microsecond // 1000:03d}"


def to_clickhouse_datetime(date: datetime) -> str:
    """Format as YYYY-MM-DD HH:MM:SS (UTC)."""
    utc_date = date.astimezone(UTC)
    return utc_date.strftime("%Y-%m-%d %H:%M:%S")
