"""Output formatting utilities for bslog."""

import io
import json
import re
from typing import Any

from rich.console import Console
from rich.table import Table

OutputFormat = str  # "json" | "table" | "csv" | "pretty"

DisplayRow = dict[str, Any]


def format_output(data: list[DisplayRow], fmt: OutputFormat = "json") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2)
    elif fmt == "pretty":
        return _format_pretty(data)
    elif fmt == "table":
        return _format_table(data)
    elif fmt == "csv":
        return _format_csv(data)
    else:
        return json.dumps(data, indent=2)


def _format_pretty(data: list[DisplayRow]) -> str:
    output: list[str] = []

    for entry in data:
        timestamp_value = entry.get("dt", "No timestamp")
        if not isinstance(timestamp_value, str):
            timestamp_value = "No timestamp"

        level = entry.get("level") if isinstance(entry.get("level"), str) else extract_level(entry)

        if level:
            level_lower = level.lower()
            if level_lower in ("error", "fatal"):
                level_text = f"[red]{level.upper()}[/red]"
            elif level_lower in ("warn", "warning"):
                level_text = f"[yellow]{level.upper()}[/yellow]"
            elif level_lower == "info":
                level_text = f"[blue]{level.upper()}[/blue]"
            elif level_lower == "debug":
                level_text = f"[dim]{level.upper()}[/dim]"
            else:
                level_text = f"[white]{level.upper()}[/white]"
        else:
            level_text = "[dim]LOG[/dim]"

        message = extract_message(entry)
        subsystem = (
            entry.get("subsystem")
            if isinstance(entry.get("subsystem"), str) and entry.get("subsystem")
            else extract_subsystem(entry)
        )

        line = f"[dim]{timestamp_value}[/dim] {level_text}"
        if subsystem:
            line += f" [cyan]\\[{subsystem}][/cyan]"
        line += f" {message}"

        # Render with Rich to get ANSI codes
        buf = io.StringIO()
        temp_console = Console(file=buf, highlight=False, force_terminal=True, width=200)
        temp_console.print(line, end="")
        output.append(buf.getvalue())

        extra_fields = _get_extra_fields(entry)
        if extra_fields:
            for key, value in extra_fields.items():
                extra_buf = io.StringIO()
                temp_console2 = Console(file=extra_buf, highlight=False, force_terminal=True, width=200)
                temp_console2.print(f"  [dim]{key}[/dim]: {_format_value(value)}", end="")
                output.append(extra_buf.getvalue())

    return "\n".join(output)


def _format_table(data: list[DisplayRow]) -> str:
    if not data:
        return "No results found"

    all_keys: list[str] = []
    seen: set[str] = set()
    for entry in data:
        for key in entry:
            if key not in seen:
                seen.add(key)
                all_keys.append(key)

    table = Table(show_header=True, header_style="bold")
    for key in all_keys:
        if key == "dt":
            table.add_column(key, width=20)
        elif key == "raw":
            table.add_column(key, width=50)
        elif key == "message":
            table.add_column(key, width=40)
        else:
            table.add_column(key)

    for entry in data:
        row: list[str] = []
        for key in all_keys:
            value = entry.get(key)
            if value is None:
                row.append("")
            elif isinstance(value, dict) or isinstance(value, list):
                row.append(json.dumps(value))
            else:
                row.append(str(value))
        table.add_row(*row)

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=200)
    console.print(table, end="")
    return buf.getvalue()


def _format_csv(data: list[DisplayRow]) -> str:
    if not data:
        return ""

    all_keys: list[str] = []
    seen: set[str] = set()
    for entry in data:
        for key in entry:
            if key not in seen:
                seen.add(key)
                all_keys.append(key)

    lines: list[str] = []
    lines.append(",".join(_escape_csv(h) for h in all_keys))

    for entry in data:
        row: list[str] = []
        for key in all_keys:
            value = entry.get(key)
            if value is None:
                row.append("")
            elif isinstance(value, dict) or isinstance(value, list):
                row.append(_escape_csv(json.dumps(value)))
            else:
                row.append(_escape_csv(str(value)))
        lines.append(",".join(row))

    return "\n".join(lines)


def _escape_csv(value: str) -> str:
    if "," in value or '"' in value or "\n" in value:
        return f'"{value.replace(chr(34), chr(34) + chr(34))}"'
    return value


def extract_level(entry: DisplayRow) -> str | None:
    level = entry.get("level")
    if isinstance(level, str) and level:
        return level

    parsed = parse_raw(entry.get("raw"))
    if parsed:
        level_val = parsed.get("level")
        if isinstance(level_val, str) and level_val:
            return level_val

        severity = parsed.get("severity")
        if isinstance(severity, str) and severity:
            return severity

        vercel = parsed.get("vercel")
        if isinstance(vercel, dict):
            vercel_level = vercel.get("level")
            if isinstance(vercel_level, str) and vercel_level:
                return vercel_level
        return None

    raw = entry.get("raw")
    if isinstance(raw, str):
        match = re.search(r"\b(ERROR|WARN|WARNING|INFO|DEBUG|FATAL)\b", raw, re.IGNORECASE)
        return match.group(1) if match else None

    return None


def extract_message(entry: DisplayRow) -> str:
    message = entry.get("message")
    if isinstance(message, str) and message:
        return message

    parsed = parse_raw(entry.get("raw"))
    if parsed:
        primary = parsed.get("message") or parsed.get("msg")
        if isinstance(primary, str) and primary:
            return primary
        return json.dumps(parsed)

    raw = entry.get("raw")
    if isinstance(raw, str) and raw:
        return raw

    return json.dumps(entry)


def extract_subsystem(entry: DisplayRow) -> str | None:
    subsystem = entry.get("subsystem")
    if isinstance(subsystem, str) and subsystem:
        return subsystem

    parsed = parse_raw(entry.get("raw"))
    if parsed:
        sub = parsed.get("subsystem") or parsed.get("service") or parsed.get("component")
        if isinstance(sub, str) and sub:
            return sub

    return None


def _get_extra_fields(entry: DisplayRow) -> dict[str, Any]:
    exclude_keys = {"dt", "raw", "level", "message", "subsystem", "time", "severity"}
    extras: dict[str, Any] = {}

    raw = entry.get("raw")
    if raw is not None:
        parsed = parse_raw(raw)
        if parsed:
            for key, value in parsed.items():
                if key not in exclude_keys:
                    extras[key] = value
        else:
            extras["raw"] = raw

    for key, value in entry.items():
        if key not in exclude_keys and key != "raw":
            extras[key] = value

    return extras


def _format_value(value: Any) -> str:
    if value is None:
        return "None"

    if isinstance(value, dict) or isinstance(value, list):
        try:
            return json.dumps(value, indent=2)
        except (TypeError, ValueError):
            return str(value)

    return str(value)


def parse_raw(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            return None
        return None

    if isinstance(raw, dict):
        return raw

    return None


def format_bytes(byte_count: int) -> str:
    if byte_count == 0:
        return "0 Bytes"

    k = 1024
    sizes = ["Bytes", "KB", "MB", "GB", "TB"]
    import math

    i = int(math.floor(math.log(byte_count) / math.log(k)))
    return f"{byte_count / k ** i:.2f} {sizes[i]}"
