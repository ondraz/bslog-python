"""Tests for output formatting utilities."""

import json

from bslog.utils.formatter import format_output


class TestFormatOutput:
    sample_data = [
        {
            "dt": "2024-01-15 10:30:45.123",
            "level": "error",
            "message": "Test error message",
            "subsystem": "api",
            "userId": "12345",
        },
        {
            "dt": "2024-01-15 10:31:00.456",
            "level": "warning",
            "message": "Test warning",
            "subsystem": "database",
        },
    ]

    def test_format_as_json_by_default(self) -> None:
        result = format_output(self.sample_data)
        parsed = json.loads(result)

        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["message"] == "Test error message"

    def test_format_as_json_with_indentation(self) -> None:
        result = format_output(self.sample_data, "json")

        assert "  " in result
        assert '"dt"' in result
        assert '"level"' in result
        assert '"message"' in result

    def test_format_as_pretty_output(self) -> None:
        result = format_output(self.sample_data, "pretty")

        assert "2024-01-15 10:30:45.123" in result
        assert "ERROR" in result
        assert "[api]" in result
        assert "Test error message" in result
        assert "userId" in result
        assert "12345" in result

    def test_format_as_csv(self) -> None:
        result = format_output(self.sample_data, "csv")
        lines = result.split("\n")

        assert "dt" in lines[0]
        assert "level" in lines[0]
        assert "message" in lines[0]
        assert len(lines) == 3
        assert "2024-01-15 10:30:45.123" in lines[1]
        assert "error" in lines[1]

    def test_escape_csv_values_with_commas(self) -> None:
        data = [{"dt": "2024-01-15", "message": "Error, with comma"}]
        result = format_output(data, "csv")

        assert '"Error, with comma"' in result

    def test_escape_csv_values_with_quotes(self) -> None:
        data = [{"dt": "2024-01-15", "message": 'Error with "quotes"'}]
        result = format_output(data, "csv")

        assert '"Error with ""quotes"""' in result

    def test_format_as_table(self) -> None:
        result = format_output(self.sample_data, "table")

        assert "2024-01-15" in result
        assert "error" in result

    def test_handle_empty_data_array(self) -> None:
        result = format_output([], "json")
        assert result == "[]"

        csv_result = format_output([], "csv")
        assert csv_result == ""

        table_result = format_output([], "table")
        assert table_result == "No results found"

    def test_extract_level_from_raw_json(self) -> None:
        data = [
            {
                "dt": "2024-01-15",
                "raw": json.dumps({"level": "info", "message": "test"}),
            },
        ]
        result = format_output(data, "pretty")

        assert "INFO" in result

    def test_extract_level_from_nested_vercel_metadata(self) -> None:
        data = [
            {
                "dt": "2024-01-15",
                "raw": json.dumps({
                    "vercel": {"level": "error", "proxy": {"status_code": 500}},
                    "message": "Nested level test",
                }),
            },
        ]
        result = format_output(data, "pretty")

        assert "ERROR" in result
        assert "Nested level test" in result

    def test_extract_message_from_raw_json(self) -> None:
        data = [
            {
                "dt": "2024-01-15",
                "raw": json.dumps({"msg": "Test message from raw"}),
            },
        ]
        result = format_output(data, "pretty")

        assert "Test message from raw" in result

    def test_handle_nested_objects_in_json_output(self) -> None:
        data = [
            {
                "dt": "2024-01-15",
                "details": {"error": "nested error", "code": 500},
            },
        ]
        result = format_output(data, "json")
        parsed = json.loads(result)

        assert parsed[0]["details"]["error"] == "nested error"
        assert parsed[0]["details"]["code"] == 500

    def test_color_code_log_levels_in_pretty_format(self) -> None:
        data = [
            {"dt": "2024-01-15", "level": "error", "message": "Error"},
            {"dt": "2024-01-15", "level": "warn", "message": "Warning"},
            {"dt": "2024-01-15", "level": "info", "message": "Info"},
            {"dt": "2024-01-15", "level": "debug", "message": "Debug"},
        ]
        result = format_output(data, "pretty")

        assert "ERROR" in result
        assert "WARN" in result
        assert "INFO" in result
        assert "DEBUG" in result

    def test_handle_null_values(self) -> None:
        data = [
            {
                "dt": "2024-01-15",
                "level": None,
                "valid": "data",
            },
        ]
        json_result = format_output(data, "json")
        parsed = json.loads(json_result)

        assert parsed[0]["level"] is None
        assert parsed[0]["valid"] == "data"

    def test_handle_raw_field_with_non_json_string(self) -> None:
        data = [
            {
                "dt": "2024-01-15",
                "raw": "Plain text log entry ERROR something went wrong",
            },
        ]
        result = format_output(data, "pretty")

        assert "Plain text log entry" in result
        assert "ERROR" in result

    def test_format_extra_fields_in_pretty_output(self) -> None:
        data = [
            {
                "dt": "2024-01-15",
                "level": "info",
                "message": "Main message",
                "requestId": "req-123",
                "responseTime": 250,
                "endpoint": "/api/users",
            },
        ]
        result = format_output(data, "pretty")

        assert "requestId" in result
        assert "req-123" in result
        assert "responseTime" in result
        assert "250" in result
        assert "endpoint" in result
        assert "/api/users" in result
