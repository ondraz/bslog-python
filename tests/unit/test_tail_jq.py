"""Tests for tail jq integration."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bslog.commands.tail import _print_results, _set_jq_runner_for_tests


class TestTailJqIntegration:
    def teardown_method(self) -> None:
        _set_jq_runner_for_tests(None)

    def test_pipes_json_through_jq_when_filter_provided(self) -> None:
        jq_mock = MagicMock(return_value=SimpleNamespace(
            stdout='"trimmed"\n',
            stderr="",
            status=0,
            returncode=0,
        ))
        _set_jq_runner_for_tests(jq_mock)

        entries = [{"dt": "2025-09-24 12:00:00.000000", "raw": "{}", "message": "hello"}]

        stdout_writes: list[str] = []

        def capture_write(s: str) -> int:
            stdout_writes.append(s)
            return len(s)

        with patch.object(sys.stdout, "write", side_effect=capture_write):
            with patch("builtins.print"):
                _print_results(entries, "json", jq_filter=".[]")

        assert jq_mock.call_count == 1
        args = jq_mock.call_args
        assert args[0][0] == ".[]"
        assert '"trimmed"\n' in stdout_writes

    def test_falls_back_when_jq_exits_with_error(self) -> None:
        jq_mock = MagicMock(return_value=SimpleNamespace(
            stdout="",
            stderr="parse error",
            status=2,
            returncode=2,
        ))
        _set_jq_runner_for_tests(jq_mock)

        entries = [{"dt": "2025-09-24 12:00:00.000000", "raw": "{}", "message": "hello"}]

        stderr_writes: list[str] = []
        print_calls: list[str] = []

        def mock_print(*args: object, **kwargs: object) -> None:
            if kwargs.get("file") is sys.stderr:
                stderr_writes.append(str(args[0]) if args else "")
            else:
                print_calls.append(str(args[0]) if args else "")

        with patch("builtins.print", side_effect=mock_print):
            _print_results(entries, "json", jq_filter=".[]")

        assert jq_mock.call_count == 1
        assert any("jq exited with status 2" in s for s in stderr_writes)
        assert len(print_calls) == 1
        assert "hello" in print_calls[0]
