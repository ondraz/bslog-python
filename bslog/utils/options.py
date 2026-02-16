"""CLI option normalization utilities for bslog."""

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class RuntimeOptions:
    limit: int | None = None
    sources: list[str] | None = None
    where: dict[str, Any] | None = None
    jq: str | None = None


def normalize_sources_option(input_val: str | list[str] | None = None) -> list[str] | None:
    if not input_val:
        return None

    raw_values = input_val if isinstance(input_val, list) else [input_val]
    names: list[str] = []
    for value in raw_values:
        for name in value.split(","):
            stripped = name.strip()
            if stripped:
                names.append(stripped)

    if not names:
        return None

    return list(dict.fromkeys(names))


def parse_limit_option(raw_value: Any) -> int | None:
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, float) and raw_value == raw_value:  # not NaN
        return int(raw_value)
    if isinstance(raw_value, str):
        try:
            return int(raw_value)
        except ValueError:
            return None
    return None


def parse_where_option(input_val: str | list[str] | None = None) -> dict[str, Any] | None:
    if not input_val:
        return None

    raw_values = input_val if isinstance(input_val, list) else [input_val]
    where: dict[str, Any] = {}

    for raw in raw_values:
        if not raw:
            continue

        trimmed = raw.strip()
        if not trimmed:
            continue

        equals_index = trimmed.find("=")
        if equals_index <= 0:
            continue

        key = trimmed[:equals_index].strip()
        if not key:
            continue

        value_string: str | None = trimmed[equals_index + 1 :].strip()

        if value_string and len(value_string) >= 2:
            first_char = value_string[0]
            last_char = value_string[-1]
            if (first_char == '"' and last_char == '"') or (first_char == "'" and last_char == "'"):
                value_string = value_string[1:-1]

        parsed_value = _parse_where_value(value_string)
        where[key] = parsed_value

    return where if where else None


def _parse_where_value(value: str | None) -> Any:
    if value is None:
        return None

    if len(value) == 0:
        return ""

    lower = value.lower()
    if lower == "null":
        return None

    if lower == "true":
        return True

    if lower == "false":
        return False

    if re.match(r"^-?\d+$", value):
        return int(value)

    if re.match(r"^-?\d*\.\d+$", value):
        return float(value)

    if (value.startswith("{") and value.endswith("}")) or (value.startswith("[") and value.endswith("]")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    return value


def resolve_runtime_options(
    limit: Any = None,
    sources: str | list[str] | None = None,
    where: str | list[str] | None = None,
    jq: Any = None,
) -> RuntimeOptions:
    parsed_limit = parse_limit_option(limit)
    parsed_sources = normalize_sources_option(sources)
    parsed_where = parse_where_option(where)
    parsed_jq = jq.strip() if isinstance(jq, str) and jq.strip() else None

    return RuntimeOptions(
        limit=parsed_limit,
        sources=parsed_sources,
        where=parsed_where,
        jq=parsed_jq,
    )
