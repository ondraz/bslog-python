"""Integration tests for query builder."""

import re
import sys
from unittest.mock import MagicMock, patch

import pytest

from bslog.api.query import QueryAPI
from bslog.types import Config, QueryOptions, Source, SourceAttributes


@pytest.fixture
def mock_config():
    return Config(
        defaultSource="test-source",
        defaultLimit=100,
        outputFormat="json",
        defaultLogLevel="all",
    )


@pytest.fixture
def mock_source():
    return Source(
        id="123456",
        type="source",
        attributes=SourceAttributes(
            name="test-source",
            platform="javascript",
            token="test-token",
            team_id=123456,
            table_name="test_source",
            created_at="2024-01-01",
            updated_at="2024-01-15",
            ingesting_paused=False,
            messages_count=1000,
            bytes_count=5000,
        ),
    )


@pytest.fixture
def query_api(mock_config, mock_source):
    with patch("bslog.api.query.load_config", return_value=mock_config), \
         patch("bslog.api.query.get_query_credentials",
               return_value={"username": "test-user", "password": "test-pass"}), \
         patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
        api = QueryAPI.__new__(QueryAPI)
        api.client = MagicMock()
        api.client.query.return_value = [{"dt": "2024-01-15", "level": "info", "message": "test"}]

        mock_sources_api = MagicMock()
        mock_sources_api.find_by_name.side_effect = lambda name: mock_source if name == "test-source" else None
        api.sources_api = mock_sources_api
        yield api


class TestBuildQuery:
    def test_basic_query_with_source_and_limit(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", limit=50))

        assert "SELECT dt, raw FROM remote(t123456_test_source_logs)" in sql
        assert "ORDER BY dt DESC" in sql
        assert "LIMIT 50" in sql
        assert "FORMAT JSONEachRow" in sql

    def test_query_with_field_selection(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", fields=["dt", "level", "message"]))

        assert "SELECT dt, JSON_VALUE(raw, '$.level') AS \"level\", JSON_VALUE(raw, '$.message') AS \"message\"" in sql

    def test_query_with_nested_field_selection(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                fields=["vercel.proxy.status_code", "metadata['odd key']"],
            ))

        assert "JSON_VALUE(raw, '$.vercel.proxy.status_code') AS \"vercel.proxy.status_code\"" in sql
        assert "JSON_VALUE(raw, '$.metadata[\"odd key\"]') AS \"metadata['odd key']\"" in sql

    def test_query_with_array_index_field_selection(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                fields=["metadata.proxy[0].status"],
            ))

        assert "JSON_VALUE(raw, '$.metadata.proxy[0].status') AS \"metadata.proxy[0].status\"" in sql

    def test_query_with_root_level_bracket_selection(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                fields=['["root key"].value'],
            ))

        assert "JSON_VALUE(raw, '$[\"root key\"].value') AS \"[\"\"root key\"\"].value\"" in sql

    def test_handle_asterisk_field_selection(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", fields=["*"]))

        assert "SELECT dt, raw FROM" in sql

    def test_query_with_level_filter(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", level="error"))

        assert "JSON_VALUE(raw, '$.vercel.level')" in sql
        assert (
            "positionCaseInsensitive(COALESCE(JSONExtractString(raw, 'message'),"
            " JSON_VALUE(raw, '$.message')), 'error') > 0"
        ) in sql
        assert "JSONHas(raw, 'error')" in sql
        assert "toInt32OrZero(JSON_VALUE(raw, '$.vercel.proxy.status_code')) >= 500" in sql
        assert "= 'error'" in sql

    def test_config_default_log_level(self, query_api, mock_config) -> None:
        mock_config.defaultLogLevel = "debug"
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source"))

        assert "JSON_VALUE(raw, '$.vercel.level')" in sql
        assert "= 'debug'" in sql

    def test_explicit_level_overrides_config(self, query_api, mock_config) -> None:
        mock_config.defaultLogLevel = "debug"
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", level="info"))

        assert "= 'info'" in sql
        assert "= 'debug'" not in sql

    def test_query_with_subsystem_filter(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", subsystem="api"))

        assert "JSON_VALUE(raw, '$.subsystem') = 'api'" in sql

    def test_query_with_search_pattern(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", search="error message"))

        assert "WHERE raw LIKE '%error message%'" in sql

    def test_escape_single_quotes_in_search(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", search="user's data"))

        assert "WHERE raw LIKE '%user''s data%'" in sql

    def test_query_with_time_range(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                since="2024-01-01T00:00:00Z",
                until="2024-01-02T00:00:00Z",
            ))

        assert "WHERE dt >= toDateTime64" in sql
        assert "AND dt <= toDateTime64" in sql

    def test_query_with_where_clause(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                where={"userId": "12345", "status": "active"},
            ))

        assert "JSON_VALUE(raw, '$.userId') = '12345'" in sql
        assert "JSON_VALUE(raw, '$.status') = 'active'" in sql

    def test_query_with_nested_where_clause(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                where={"vercel.proxy.status_code": 200, "metadata['odd key']": None},
            ))

        assert "JSON_VALUE(raw, '$.vercel.proxy.status_code') = '200'" in sql
        assert "JSON_VALUE(raw, '$.metadata[\"odd key\"]') IS NULL" in sql

    def test_query_with_array_index_where_clause(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                where={"metadata.proxy[0].status": "ok"},
            ))

        assert "JSON_VALUE(raw, '$.metadata.proxy[0].status') = 'ok'" in sql

    def test_query_with_object_values_in_where_clause(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                where={"metadata": {"feature": "timeline", "enabled": True}},
            ))

        assert """JSON_VALUE(raw, '$.metadata') = '{"feature":"timeline","enabled":true}'""" in sql

    def test_where_clause_with_non_string_values(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                where={"count": 42, "active": True},
            ))

        assert "JSON_VALUE(raw, '$.count') = '42'" in sql
        assert "JSON_VALUE(raw, '$.active') = 'true'" in sql

    def test_append_union_all_with_s3_cluster_when_search_used(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", search="session-xyz"))

        assert "UNION ALL" in sql
        assert "s3Cluster(primary, t123456_test_source_s3)" in sql
        assert "_row_type = 1" in sql
        assert "dt > now() - INTERVAL 24 HOUR" in sql
        assert "raw LIKE '%session-xyz%'" in sql
        union_idx = sql.index("UNION ALL")
        order_idx = sql.index("ORDER BY")
        assert order_idx > union_idx

    def test_since_until_in_s3cluster_query(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                since="2025-01-01",
                search="test-val",
            ))

        assert "UNION ALL" in sql
        s3_part = sql.split("UNION ALL")[1]
        assert "INTERVAL 24 HOUR" not in s3_part
        assert "dt >=" in s3_part

    def test_no_union_all_when_search_not_used(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", where={"module": "auth"}))

        assert "UNION ALL" not in sql
        assert "s3Cluster" not in sql

    def test_combine_multiple_filters_with_and(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                level="error",
                subsystem="api",
                search="timeout",
            ))

        assert "WHERE" in sql
        assert "AND" in sql
        main_query = sql.split("UNION ALL")[0]
        assert len(re.findall(r"AND", main_query)) == 2

    def test_default_source_from_config(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(limit=10))

        assert "t123456_test_source_logs" in sql

    def test_default_limit_from_config(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source"))

        assert "LIMIT 100" in sql

    def test_throw_error_when_source_not_found(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            with pytest.raises(RuntimeError, match="Source not found: non-existent-source"):
                query_api.build_query(QueryOptions(source="non-existent-source"))

    def test_throw_error_when_no_source_and_no_default(self, mock_source) -> None:
        no_default_config = Config(defaultLimit=100, outputFormat="json")

        with patch("bslog.api.query.load_config", return_value=no_default_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            api = QueryAPI.__new__(QueryAPI)
            api.client = MagicMock()
            api.sources_api = MagicMock()

            with pytest.raises(RuntimeError, match="No source specified"):
                api.build_query(QueryOptions())

    def test_handle_source_names_with_hyphens(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(source="test-source", limit=1))

        assert "t123456_test_source_logs" in sql

    def test_complex_query_with_all_options(self, query_api, mock_config) -> None:
        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s):
            sql = query_api.build_query(QueryOptions(
                source="test-source",
                fields=["dt", "level", "message", "userId"],
                level="error",
                subsystem="payment",
                since="2024-01-01T00:00:00Z",
                until="2024-01-02T00:00:00Z",
                search="failed transaction",
                where={"environment": "production", "region": "us-east-1"},
                limit=500,
            ))

        assert "SELECT dt, JSON_VALUE(raw, '$.level') AS \"level\"" in sql
        assert "JSON_VALUE(raw, '$.message') AS \"message\"" in sql
        assert "JSON_VALUE(raw, '$.userId') AS \"userId\"" in sql
        assert "JSON_VALUE(raw, '$.vercel.level')" in sql
        assert "JSON_VALUE(raw, '$.subsystem') = 'payment'" in sql
        assert "dt >= toDateTime64" in sql
        assert "dt <= toDateTime64" in sql
        assert "raw LIKE '%failed transaction%'" in sql
        assert "JSON_VALUE(raw, '$.environment') = 'production'" in sql
        assert "JSON_VALUE(raw, '$.region') = 'us-east-1'" in sql
        assert "LIMIT 500" in sql


class TestExecuteVerboseMode:
    def test_log_sql_when_verbose_true(self, query_api, mock_config) -> None:
        stderr_output: list[str] = []

        def capture_stderr(*args, **kwargs):
            stderr_output.append(str(args[0]) if args else "")

        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s), \
             patch("bslog.api.query.get_query_credentials", return_value={"username": "u", "password": "p"}), \
             patch("builtins.print", side_effect=capture_stderr):
            query_api.execute(QueryOptions(source="test-source", verbose=True, limit=10))

        assert any("Executing query: SELECT dt, raw FROM remote(t123456_test_source_logs)" in s for s in stderr_output)

    def test_no_log_when_verbose_false(self, query_api, mock_config) -> None:
        stderr_output: list[str] = []

        def capture_stderr(*args, **kwargs):
            if kwargs.get("file") is sys.stderr:
                stderr_output.append(str(args[0]) if args else "")

        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s), \
             patch("bslog.api.query.get_query_credentials", return_value={"username": "u", "password": "p"}), \
             patch("builtins.print", side_effect=capture_stderr):
            query_api.execute(QueryOptions(source="test-source", verbose=False, limit=10))

        assert not any("Executing query" in s for s in stderr_output)

    def test_no_log_when_verbose_undefined(self, query_api, mock_config) -> None:
        stderr_output: list[str] = []

        def capture_stderr(*args, **kwargs):
            if kwargs.get("file") is sys.stderr:
                stderr_output.append(str(args[0]) if args else "")

        with patch("bslog.api.query.load_config", return_value=mock_config), \
             patch("bslog.api.query.resolve_source_alias", side_effect=lambda s: s), \
             patch("bslog.api.query.get_query_credentials", return_value={"username": "u", "password": "p"}), \
             patch("builtins.print", side_effect=capture_stderr):
            query_api.execute(QueryOptions(source="test-source", limit=10))

        assert not any("Executing query" in s for s in stderr_output)
