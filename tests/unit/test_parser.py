"""Tests for the GraphQL query parser."""

import pytest

from bslog.parser.graphql import parse_graphql_query


class TestParseGraphQLQuery:
    def test_simple_query_with_limit(self) -> None:
        query = "{ logs(limit: 100) { dt, level, message } }"
        result = parse_graphql_query(query)

        assert result.limit == 100
        assert result.fields == ["dt", "level", "message"]

    def test_query_with_level_filter(self) -> None:
        query = "{ logs(level: 'error', limit: 50) { * } }"
        result = parse_graphql_query(query)

        assert result.level == "error"
        assert result.limit == 50
        assert result.fields is None

    def test_query_with_time_range(self) -> None:
        query = "{ logs(since: '1h', until: '30m') { dt, message } }"
        result = parse_graphql_query(query)

        assert result.since == "1h"
        assert result.until == "30m"
        assert result.fields == ["dt", "message"]

    def test_query_with_between_syntax(self) -> None:
        query = "{ logs(between: ['2024-01-01', '2024-01-02']) { * } }"
        result = parse_graphql_query(query)

        assert result.since == "2024-01-01"
        assert result.until == "2024-01-02"

    def test_query_with_subsystem_filter(self) -> None:
        query = "{ logs(subsystem: 'api') { dt, message } }"
        result = parse_graphql_query(query)

        assert result.subsystem == "api"

    def test_query_with_search_parameter(self) -> None:
        query = "{ logs(search: 'database error') { * } }"
        result = parse_graphql_query(query)

        assert result.search == "database error"

    def test_query_with_where_clause(self) -> None:
        query = "{ logs(where: { userId: '12345', status: 'active' }) { * } }"
        result = parse_graphql_query(query)

        assert result.where == {"userId": "12345", "status": "active"}

    def test_query_with_source_parameter(self) -> None:
        query = "{ logs(source: 'production') { dt } }"
        result = parse_graphql_query(query)

        assert result.source == "production"

    def test_complex_query_with_multiple_parameters(self) -> None:
        query = """{
            logs(
                level: 'error',
                subsystem: 'payment',
                since: '1h',
                limit: 200,
                where: { environment: 'prod' }
            ) {
                dt,
                message,
                stack_trace
            }
        }"""
        result = parse_graphql_query(query)

        assert result.level == "error"
        assert result.subsystem == "payment"
        assert result.since == "1h"
        assert result.limit == 200
        assert result.where == {"environment": "prod"}
        assert result.fields == ["dt", "message", "stack_trace"]

    def test_query_without_parameters(self) -> None:
        query = "{ logs() { dt, message } }"
        result = parse_graphql_query(query)

        assert result.fields == ["dt", "message"]
        assert result.limit is None

    def test_query_with_asterisk_for_all_fields(self) -> None:
        query = "{ logs(limit: 10) { * } }"
        result = parse_graphql_query(query)

        assert result.limit == 10
        assert result.fields is None

    def test_invalid_query_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid query format"):
            parse_graphql_query("invalid query")

    def test_boolean_values(self) -> None:
        query = "{ logs(where: { active: true, deleted: false }) { * } }"
        result = parse_graphql_query(query)

        assert result.where == {"active": True, "deleted": False}

    def test_numeric_values(self) -> None:
        query = "{ logs(limit: 100, where: { count: 42 }) { * } }"
        result = parse_graphql_query(query)

        assert result.limit == 100
        assert result.where == {"count": 42}

    def test_trim_whitespace_from_field_names(self) -> None:
        query = "{ logs() {  dt , level , message  } }"
        result = parse_graphql_query(query)

        assert result.fields == ["dt", "level", "message"]

    def test_both_single_and_double_quotes(self) -> None:
        result1 = parse_graphql_query('{ logs(level: "error") { * } }')
        result2 = parse_graphql_query("{ logs(level: 'error') { * } }")

        assert result1.level == "error"
        assert result2.level == "error"
