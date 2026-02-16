"""Query API for ClickHouse SQL execution against Better Stack."""

import json
import re
import sys
from typing import Any

from bslog.api.client import BetterStackClient
from bslog.api.sources import SourcesAPI
from bslog.types import QueryOptions
from bslog.utils.config import get_query_credentials, load_config, resolve_source_alias
from bslog.utils.time import parse_time_string, to_clickhouse_datetime

VALID_IDENTIFIER_REGEX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def escape_sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "''")


class QueryAPI:
    def __init__(self) -> None:
        self.client = BetterStackClient()
        self.sources_api = SourcesAPI()

    def _build_json_path(self, field: str) -> str:
        trimmed = field.strip()
        if trimmed.startswith("$"):
            return trimmed

        segments: list[str] = []
        buffer = ""
        in_bracket = False
        quote_char: str | None = None

        def flush_plain() -> None:
            nonlocal buffer
            segment = buffer.strip()
            if segment:
                segments.append(segment)
            buffer = ""

        def flush_bracket() -> None:
            nonlocal buffer
            if buffer:
                segments.append(buffer)
            buffer = ""

        for index in range(len(trimmed)):
            char = trimmed[index]

            if not in_bracket:
                if char == ".":
                    flush_plain()
                    continue
                if char == "[":
                    flush_plain()
                    in_bracket = True
                    buffer = "["
                    quote_char = None
                    continue
                buffer += char
                continue

            buffer += char

            if char in ('"', "'"):
                previous = trimmed[index - 1] if index > 0 else ""
                if quote_char == char and previous != "\\":
                    quote_char = None
                elif not quote_char:
                    quote_char = char
            elif char == "]" and not quote_char:
                flush_bracket()
                in_bracket = False

        if buffer:
            if in_bracket:
                segments.append(buffer)
            else:
                flush_plain()

        path = "$"
        for segment in segments:
            if not segment:
                continue
            if segment.startswith("["):
                path += self._normalize_bracket_segment(segment)
            else:
                path += self._normalize_plain_segment(segment)

        return path

    def _build_json_accessor(self, field: str) -> str:
        path = self._build_json_path(field)
        return f"JSON_VALUE(raw, '{path}')"

    def _normalize_plain_segment(self, segment: str) -> str:
        cleaned = segment.strip()
        if not cleaned:
            return ""

        if VALID_IDENTIFIER_REGEX.match(cleaned):
            return f".{cleaned}"

        escaped = cleaned.replace("\\", "\\\\").replace('"', '\\"')
        return f'["{escaped}"]'

    def _normalize_bracket_segment(self, segment: str) -> str:
        if not segment.startswith("[") or not segment.endswith("]"):
            return self._normalize_plain_segment(segment)

        inner = segment[1:-1].strip()
        if not inner:
            return segment

        if inner == "*":
            return "[*]"

        quote = inner[0]
        is_quoted = quote in ('"', "'")
        if is_quoted and inner[-1] == quote:
            key = inner[1:-1]
            # Remove escape sequences for quotes
            key = re.sub(r"\\(['\"])", r"\1", key)
            escaped = key.replace("\\", "\\\\").replace('"', '\\"')
            return f'["{escaped}"]'

        if re.match(r"^-?\d+$", inner):
            return f"[{inner}]"

        escaped = inner.replace("\\", "\\\\").replace('"', '\\"')
        return f'["{escaped}"]'

    def build_query(self, options: QueryOptions) -> str:
        config = load_config()
        config_level = (
            config.defaultLogLevel
            if config.defaultLogLevel and config.defaultLogLevel.lower() != "all"
            else None
        )
        effective_level = options.level if options.level is not None else config_level

        raw_source_name = options.source or config.defaultSource
        source_name = resolve_source_alias(raw_source_name)

        if not source_name:
            raise RuntimeError(
                "No source specified. Use --source or set a default source with: bslog config source <name>"
            )

        source = self.sources_api.find_by_name(source_name)
        if not source:
            raise RuntimeError(f"Source not found: {source_name}")

        table_prefix = f"t{source.attributes.team_id}_{source.attributes.table_name}"
        table_name = f"{table_prefix}_logs"
        fields = (
            self._build_field_selection(options.fields) if options.fields and len(options.fields) > 0 else "dt, raw"
        )

        sql = f"SELECT {fields} FROM remote({table_name})"

        conditions: list[str] = []

        if options.since:
            since_date = parse_time_string(options.since)
            conditions.append(f"dt >= toDateTime64('{to_clickhouse_datetime(since_date)}', 3)")

        if options.until:
            until_date = parse_time_string(options.until)
            conditions.append(f"dt <= toDateTime64('{to_clickhouse_datetime(until_date)}', 3)")

        if effective_level:
            escaped_level = effective_level.replace("'", "''").lower()
            level_expression = (
                "lowerUTF8(COALESCE("
                "JSONExtractString(raw, 'level'),"
                "JSON_VALUE(raw, '$.level'),"
                "JSON_VALUE(raw, '$.levelName'),"
                "JSON_VALUE(raw, '$.vercel.level')\n      ))"
            )
            message_expression = "COALESCE(JSONExtractString(raw, 'message'), JSON_VALUE(raw, '$.message'))"
            status_expression = "toInt32OrZero(JSON_VALUE(raw, '$.vercel.proxy.status_code'))"

            if escaped_level == "error":
                conditions.append(
                    f"({level_expression} = '{escaped_level}'"
                    f" OR {status_expression} >= 500"
                    f" OR positionCaseInsensitive({message_expression}, 'error') > 0"
                    f" OR JSONHas(raw, 'error'))"
                )
            elif escaped_level in ("warning", "warn"):
                conditions.append(
                    f"({level_expression} IN ('{escaped_level}', 'warning', 'warn')"
                    f" OR ({status_expression} >= 400 AND {status_expression} < 500))"
                )
            else:
                conditions.append(f"{level_expression} = '{escaped_level}'")

        if options.subsystem:
            subsystem_accessor = self._build_json_accessor("subsystem")
            conditions.append(f"{subsystem_accessor} = '{escape_sql_string(options.subsystem)}'")

        if options.search:
            conditions.append(f"raw LIKE '%{escape_sql_string(options.search)}%'")

        where_conditions: list[str] = []

        if options.where:
            for key, value in options.where.items():
                accessor = self._build_json_accessor(key)

                if value is None:
                    where_conditions.append(f"{accessor} IS NULL")
                elif isinstance(value, str):
                    where_conditions.append(f"{accessor} = '{escape_sql_string(value)}'")
                elif isinstance(value, bool):
                    where_conditions.append(f"{accessor} = '{str(value).lower()}'")
                else:
                    serialized = (
                        json.dumps(value, separators=(",", ":"))
                        if isinstance(value, (dict, list))
                        else str(value)
                    )
                    where_conditions.append(f"{accessor} = '{escape_sql_string(serialized)}'")

            conditions.extend(where_conditions)

        if conditions:
            sql += f" WHERE {' AND '.join(conditions)}"

        # Append UNION ALL with S3 cluster query when search is used
        if options.search:
            s3_name = f"{table_prefix}_s3"
            s3_conditions: list[str] = ["_row_type = 1"]

            if options.since:
                since_date = parse_time_string(options.since)
                s3_conditions.append(f"dt >= toDateTime64('{to_clickhouse_datetime(since_date)}', 3)")
            else:
                s3_conditions.append("dt > now() - INTERVAL 24 HOUR")

            if options.until:
                until_date = parse_time_string(options.until)
                s3_conditions.append(f"dt <= toDateTime64('{to_clickhouse_datetime(until_date)}', 3)")

            s3_conditions.append(f"raw LIKE '%{escape_sql_string(options.search)}%'")
            s3_conditions.extend(where_conditions)

            sql += f" UNION ALL SELECT {fields} FROM s3Cluster(primary, {s3_name})"
            sql += f" WHERE {' AND '.join(s3_conditions)}"

        sql += " ORDER BY dt DESC"
        sql += f" LIMIT {options.limit or config.defaultLimit or 100}"
        sql += " FORMAT JSONEachRow"

        return sql

    def _build_field_selection(self, fields: list[str]) -> str:
        selections: list[str] = ["dt"]

        for field in fields:
            if field in ("*", "raw"):
                selections.append("raw")
                continue
            if field == "dt":
                continue

            accessor = self._build_json_accessor(field)
            escaped_alias = field.replace('"', '""')
            selections.append(f'{accessor} AS "{escaped_alias}"')

        return ", ".join(selections)

    def execute(self, options: QueryOptions) -> list[dict[str, Any]]:
        sql = self.build_query(options)

        if options.verbose:
            print(f"Executing query: {sql}", file=sys.stderr)

        credentials = get_query_credentials()
        return self.client.query(sql, credentials.get("username"), credentials.get("password"))

    def execute_sql(self, sql: str) -> list[dict[str, Any]]:
        statement = sql
        if "format" not in statement.lower():
            statement = f"{statement} FORMAT JSONEachRow"

        credentials = get_query_credentials()
        return self.client.query(statement, credentials.get("username"), credentials.get("password"))
