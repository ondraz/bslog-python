"""GraphQL-inspired query parser for bslog."""

import re
from typing import Any

from bslog.types import QueryOptions


def parse_graphql_query(query: str) -> QueryOptions:
    normalized = query.strip()
    if normalized.startswith("{") and normalized.endswith("}"):
        normalized = normalized[1:-1].strip()

    logs_match = re.search(r"logs\s*\((.*?)\)\s*\{(.*?)\}", normalized, re.DOTALL)
    if not logs_match:
        raise ValueError("Invalid query format. Expected: { logs(...) { ... } }")

    args_str = logs_match.group(1)
    fields_str = logs_match.group(2)

    options = QueryOptions()

    if args_str:
        args = _parse_arguments(args_str)

        if args.get("limit") is not None:
            options.limit = int(args["limit"])

        if args.get("level"):
            options.level = str(args["level"])

        if args.get("subsystem"):
            options.subsystem = str(args["subsystem"])

        if args.get("since"):
            options.since = str(args["since"])

        if args.get("until"):
            options.until = str(args["until"])

        between = args.get("between")
        if isinstance(between, list) and len(between) == 2:
            options.since = str(between[0])
            options.until = str(between[1])

        if args.get("search"):
            options.search = str(args["search"])

        if isinstance(args.get("where"), dict):
            options.where = args["where"]

        if args.get("source"):
            options.source = str(args["source"])

    if fields_str:
        fields = [f.strip() for f in fields_str.split(",") if f.strip()]
        if fields and fields[0] != "*":
            options.fields = fields

    return options


def _parse_arguments(args_str: str) -> dict[str, Any]:
    result: dict[str, Any] = {}

    current_key = ""
    current_value = ""
    depth = 0
    in_string = False
    string_char = ""

    for i in range(len(args_str)):
        char = args_str[i]

        if in_string:
            if char == string_char and (i == 0 or args_str[i - 1] != "\\"):
                in_string = False
            current_value += char
        elif char in ('"', "'"):
            in_string = True
            string_char = char
            current_value += char
        elif char in ("{", "["):
            depth += 1
            current_value += char
        elif char in ("}", "]"):
            depth -= 1
            current_value += char
        elif char == ":" and depth == 0 and not current_key:
            current_key = current_value.strip()
            current_value = ""
        elif char == "," and depth == 0:
            if current_key:
                result[current_key] = _parse_value(current_value.strip())
                current_key = ""
                current_value = ""
        else:
            current_value += char

    if current_key and current_value:
        result[current_key] = _parse_value(current_value.strip())

    return result


def _parse_value(value: str) -> Any:
    # Remove quotes from strings
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]

    # Parse numbers
    if re.match(r"^\d+$", value):
        return int(value)

    # Parse booleans
    if value == "true":
        return True
    if value == "false":
        return False

    # Parse objects
    if value.startswith("{") and value.endswith("}"):
        try:
            obj_str = value[1:-1]
            obj: dict[str, Any] = {}
            pairs = obj_str.split(",")

            for pair in pairs:
                parts = pair.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key and val:
                        obj[key] = _parse_value(val)

            return obj
        except Exception:
            return value

    # Parse arrays
    if value.startswith("[") and value.endswith("]"):
        try:
            arr_str = value[1:-1]
            return [_parse_value(s.strip()) for s in arr_str.split(",")]
        except Exception:
            return value

    return value
