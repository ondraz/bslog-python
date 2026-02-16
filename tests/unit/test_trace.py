"""Tests for trace command."""

from bslog.commands.trace import trace_request


class TestTraceRequest:
    def test_adds_request_id_to_where_clause(self) -> None:
        original_where = {"module": "api"}
        call_log: list[dict] = []

        def mock_executor(**kwargs):
            call_log.append(kwargs)

        trace_request(
            "abc-123",
            where=original_where,
            sources=["dev"],
            fmt="json",
            executor=mock_executor,
        )

        assert len(call_log) == 1
        call_options = call_log[0]

        assert call_options["where"] == {"module": "api", "requestId": "abc-123"}
        assert call_options["sources"] == ["dev"]
        # Original where dict should not be mutated
        assert original_where == {"module": "api"}
