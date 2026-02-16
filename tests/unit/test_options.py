"""Tests for CLI option helpers."""

from bslog.utils.options import (
    normalize_sources_option,
    parse_limit_option,
    parse_where_option,
    resolve_runtime_options,
)


class TestNormalizeSourcesOption:
    def test_returns_none_for_empty_input(self) -> None:
        assert normalize_sources_option(None) is None
        assert normalize_sources_option("") is None

    def test_deduplicates_and_trims_sources(self) -> None:
        assert normalize_sources_option(["prod,dev", " prod "]) == ["prod", "dev"]


class TestParseLimitOption:
    def test_parses_numeric_values(self) -> None:
        assert parse_limit_option("200") == 200
        assert parse_limit_option(50) == 50

    def test_returns_none_for_invalid_values(self) -> None:
        assert parse_limit_option("foo") is None


class TestParseWhereOption:
    def test_parses_simple_equality(self) -> None:
        assert parse_where_option(["module=timeline", "env=production"]) == {
            "module": "timeline",
            "env": "production",
        }

    def test_parses_typed_values(self) -> None:
        result = parse_where_option(["attempt=5", "active=true", "deleted=false", "userId=null"])
        assert result == {
            "attempt": 5,
            "active": True,
            "deleted": False,
            "userId": None,
        }

    def test_parses_quoted_and_json_values(self) -> None:
        result = parse_where_option(["route='/api/timeline'", 'meta={"flag":true}', "ids=[1,2]"])
        assert result == {
            "route": "/api/timeline",
            "meta": {"flag": True},
            "ids": [1, 2],
        }

    def test_returns_none_when_no_valid_filters(self) -> None:
        assert parse_where_option([]) is None
        assert parse_where_option(["invalid"]) is None


class TestResolveRuntimeOptions:
    def test_combines_parsed_options(self) -> None:
        result = resolve_runtime_options(
            limit="25",
            sources="prod,dev",
            where=["module=timeline"],
            jq=".[]",
        )

        assert result.limit == 25
        assert result.sources == ["prod", "dev"]
        assert result.where == {"module": "timeline"}
        assert result.jq == ".[]"
