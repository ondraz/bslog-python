"""Tests for multi-source tail correlation."""

import json
from unittest.mock import MagicMock, patch

from bslog.commands.tail import tail_logs


class TestTailMultiSource:
    def test_merges_multiple_sources_and_annotates(self) -> None:
        fixtures = {
            "source-a": [
                {"dt": "2025-09-24 12:00:05.000000", "raw": "{}", "message": "A newest"},
                {"dt": "2025-09-24 11:59:00.000000", "raw": "{}", "message": "A older"},
            ],
            "source-b": [
                {"dt": "2025-09-24 12:00:07.000000", "raw": "{}", "message": "B newest"},
                {"dt": "2025-09-24 12:00:01.000000", "raw": "{}", "message": "B older"},
            ],
        }

        call_log: list[dict] = []
        print_calls: list[str] = []

        def mock_execute(options):
            call_log.append({"source": options.source, "limit": options.limit})
            source_name = options.source or ""
            dataset = fixtures.get(source_name, [])
            limit_val = options.limit or 100
            return dataset[:limit_val]

        def mock_print(*args, **kwargs):
            if args:
                print_calls.append(str(args[0]))

        with patch("bslog.commands.tail.QueryAPI") as mock_query_api, \
             patch("bslog.commands.tail.load_config") as mock_config, \
             patch("bslog.commands.tail.resolve_source_alias", side_effect=lambda x: x), \
             patch("builtins.print", side_effect=mock_print):

            mock_config.return_value = MagicMock(defaultSource=None)
            mock_api = mock_query_api.return_value
            mock_api.execute = mock_execute

            tail_logs(sources=["source-a", "source-b"], fmt="json", limit=3)

        assert len(call_log) == 2
        called_sources = {c["source"] for c in call_log}
        assert called_sources == {"source-a", "source-b"}

        assert len(print_calls) == 1
        payload = json.loads(print_calls[0])

        assert isinstance(payload, list)
        assert len(payload) == 3
        assert [e["source"] for e in payload] == ["source-b", "source-a", "source-b"]
        assert payload[0]["dt"] == "2025-09-24 12:00:07.000000"
