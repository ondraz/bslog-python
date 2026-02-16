"""Tests for time utilities."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from bslog.utils.time import format_date_time, parse_time_string, to_clickhouse_datetime


class TestParseTimeString:
    def test_parse_relative_hours(self) -> None:
        now = datetime.now(tz=UTC)
        result = parse_time_string("1h")
        expected = now - timedelta(hours=1)

        assert abs((result - expected).total_seconds()) < 2

    def test_parse_relative_days(self) -> None:
        now = datetime.now(tz=UTC)
        result = parse_time_string("2d")
        expected = now - timedelta(days=2)

        assert abs((result - expected).total_seconds()) < 2

    def test_parse_relative_minutes(self) -> None:
        now = datetime.now(tz=UTC)
        result = parse_time_string("30m")
        expected = now - timedelta(minutes=30)

        assert abs((result - expected).total_seconds()) < 2

    def test_parse_relative_weeks(self) -> None:
        now = datetime.now(tz=UTC)
        result = parse_time_string("1w")
        expected = now - timedelta(weeks=1)

        assert abs((result - expected).total_seconds()) < 2

    def test_parse_iso_date_strings(self) -> None:
        result = parse_time_string("2024-01-15T10:30:00Z")
        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

    def test_parse_date_only_strings(self) -> None:
        result = parse_time_string("2024-01-15")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_invalid_time_unit(self) -> None:
        with pytest.raises(ValueError, match="Unknown time unit: x"):
            parse_time_string("5x")

    def test_invalid_date_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid time format: invalid-date"):
            parse_time_string("invalid-date")


class TestFormatDateTime:
    def test_format_date_to_readable_string(self) -> None:
        date = datetime(2024, 1, 15, 10, 30, 45, 123000, tzinfo=UTC)
        result = format_date_time(date)

        assert result == "2024-01-15 10:30:45.123"


class TestToClickHouseDateTime:
    def test_format_date_for_clickhouse(self) -> None:
        date = datetime(2024, 1, 15, 10, 30, 45, 123000, tzinfo=UTC)
        result = to_clickhouse_datetime(date)

        assert result == "2024-01-15 10:30:45"

    def test_pad_single_digit_values(self) -> None:
        date = datetime(2024, 1, 5, 5, 5, 5, tzinfo=UTC)
        result = to_clickhouse_datetime(date)

        assert result == "2024-01-05 05:05:05"

    def test_convert_timezone_to_utc(self) -> None:
        date = datetime(2024, 1, 15, 5, 30, 45, tzinfo=timezone(timedelta(hours=-5)))
        result = to_clickhouse_datetime(date)

        assert result == "2024-01-15 10:30:45"
