"""Tail command for streaming logs."""

import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

from rich.console import Console

from bslog.api.query import QueryAPI
from bslog.types import QueryOptions
from bslog.utils.config import load_config, resolve_source_alias
from bslog.utils.formatter import OutputFormat, format_output

console = Console(stderr=True)

# Allow test injection of jq runner
_jq_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None


def _set_jq_runner_for_tests(runner: Callable[..., Any] | None = None) -> None:
    global _jq_runner
    _jq_runner = runner


def tail_logs(
    source: str | None = None,
    level: str | None = None,
    subsystem: str | None = None,
    follow: bool = False,
    interval: int = 2000,
    fmt: str = "pretty",
    jq_filter: str | None = None,
    sources: list[str] | None = None,
    fields: str | list[str] | None = None,
    limit: int | None = None,
    since: str | None = None,
    until: str | None = None,
    search: str | None = None,
    where: dict[str, Any] | None = None,
    verbose: bool = False,
) -> None:
    api = QueryAPI()
    config = load_config()

    query_options = QueryOptions(
        level=level,
        subsystem=subsystem,
        since=since,
        until=until,
        search=search,
        where=where,
        verbose=verbose,
        source=source,
    )

    normalized_fields = _normalize_fields_option(fields)
    if normalized_fields:
        query_options.fields = normalized_fields

    query_options.limit = _normalize_limit(limit)

    resolved_source = resolve_source_alias(query_options.source)
    if resolved_source:
        query_options.source = resolved_source

    resolved_sources: set[str] = set()
    if resolved_source:
        resolved_sources.add(resolved_source)

    if sources:
        for candidate in sources:
            resolved = resolve_source_alias(candidate)
            if resolved:
                resolved_sources.add(resolved)

    if not resolved_sources:
        default_source = resolve_source_alias(config.defaultSource)
        if default_source:
            resolved_sources.add(default_source)

    try:
        if len(resolved_sources) <= 1:
            if len(resolved_sources) == 1:
                query_options.source = next(iter(resolved_sources))

            if query_options.source is None:
                query_options.source = resolved_source

            _run_single_source(api, query_options, follow=follow, interval=interval, fmt=fmt, jq_filter=jq_filter)
            return

        query_options.source = None
        _run_multi_source(
            api, query_options, list(resolved_sources), follow=follow, interval=interval, fmt=fmt, jq_filter=jq_filter
        )
    except Exception as e:
        console.print(f"[red]Tail error: {e}[/red]")
        sys.exit(1)


def _run_single_source(
    api: QueryAPI,
    options: QueryOptions,
    follow: bool = False,
    interval: int = 2000,
    fmt: str = "pretty",
    jq_filter: str | None = None,
) -> None:
    output_format = _resolve_format(fmt, jq_filter)
    last_timestamp: str | None = None

    results = api.execute(options)

    if results:
        _print_results(results, output_format, jq_filter)
        last_timestamp = results[0].get("dt")

    if not follow:
        return

    console.print("\n[dim]Following logs... (Press Ctrl+C to stop)[/dim]")
    interval_s = _resolve_interval(interval) / 1000
    poll_limit = max(1, min(50, options.limit or 50))
    since_fallback = options.since or "1m"

    try:
        while True:
            time.sleep(interval_s)
            try:
                poll_options = QueryOptions(
                    source=options.source,
                    level=options.level,
                    subsystem=options.subsystem,
                    search=options.search,
                    where=options.where,
                    fields=options.fields,
                    verbose=options.verbose,
                    limit=poll_limit,
                    since=last_timestamp or since_fallback,
                )

                new_results = api.execute(poll_options)
                if not new_results:
                    continue

                filtered = (
                    [
                        entry for entry in new_results
                        if not last_timestamp or entry.get("dt", "") > last_timestamp
                    ]
                    if last_timestamp
                    else new_results
                )
                if not filtered:
                    continue

                _print_results(filtered, output_format, jq_filter)
                last_timestamp = filtered[0].get("dt")
            except Exception as e:
                console.print(f"[red]Polling error: {e}[/red]")
    except KeyboardInterrupt:
        pass


def _run_multi_source(
    api: QueryAPI,
    base_options: QueryOptions,
    sources: list[str],
    follow: bool = False,
    interval: int = 2000,
    fmt: str = "pretty",
    jq_filter: str | None = None,
) -> None:
    output_format = _resolve_format(fmt, jq_filter)
    limit = base_options.limit or 100
    per_source_latest: dict[str, str] = {}

    def collect(
        since_map: dict[str, str] | None = None,
        limit_override: int | None = None,
        fallback_since: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        limit_per_source = max(1, limit_override or limit)
        combined: list[dict[str, Any]] = []
        latest_by_source: dict[str, str] = {}

        for source in sources:
            per_source_options = QueryOptions(
                source=source,
                level=base_options.level,
                subsystem=base_options.subsystem,
                search=base_options.search,
                where=base_options.where,
                fields=base_options.fields,
                verbose=base_options.verbose,
                limit=limit_per_source,
            )

            since_candidate = (since_map or {}).get(source) or base_options.since or fallback_since
            per_source_options.since = since_candidate or None

            result = api.execute(per_source_options)
            if result:
                latest_by_source[source] = result[0].get("dt", "")
                for entry in result:
                    entry_with_source = {**entry, "source": source}
                    combined.append(entry_with_source)

        combined.sort(key=lambda x: x.get("dt", ""), reverse=True)
        return combined[:limit_per_source], latest_by_source

    initial_combined, latest_by_source = collect()
    for source, dt in latest_by_source.items():
        per_source_latest[source] = dt

    if initial_combined:
        _print_results(initial_combined, output_format, jq_filter)

    if not follow:
        return

    console.print("\n[dim]Following logs... (Press Ctrl+C to stop)[/dim]")
    interval_s = _resolve_interval(interval) / 1000
    poll_limit = max(1, min(50, limit))
    fallback_since = None if base_options.since else "1m"

    try:
        while True:
            time.sleep(interval_s)
            try:
                combined, follow_latest = collect(per_source_latest, poll_limit, fallback_since)

                if combined:
                    new_entries = [
                        entry
                        for entry in combined
                        if not per_source_latest.get(entry.get("source", ""))
                        or entry.get("dt", "") > per_source_latest.get(entry.get("source", ""), "")
                    ]

                    if new_entries:
                        _print_results(new_entries, output_format, jq_filter)

                for source, dt in follow_latest.items():
                    previous = per_source_latest.get(source)
                    if not previous or dt > previous:
                        per_source_latest[source] = dt
            except Exception as e:
                console.print(f"[red]Polling error: {e}[/red]")
    except KeyboardInterrupt:
        pass


def _resolve_format(fmt: str | None, jq_filter: str | None = None) -> OutputFormat:
    if jq_filter:
        return "json"
    if fmt in ("json", "table", "csv", "pretty"):
        return fmt
    return "pretty"


def _resolve_interval(value: int | str | None) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        try:
            parsed = int(value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return 2000


def _normalize_limit(limit: int | None) -> int:
    if isinstance(limit, int) and limit > 0:
        return limit
    return 100


def _normalize_fields_option(fields: str | list[str] | None) -> list[str] | None:
    if not fields:
        return None

    raw_values = fields if isinstance(fields, list) else [fields]
    names: list[str] = []
    for value in raw_values:
        for name in value.split(","):
            stripped = name.strip()
            if stripped:
                names.append(stripped)

    if not names:
        return None

    return list(dict.fromkeys(names))


def show_errors(**kwargs: Any) -> None:
    tail_logs(level="error", **kwargs)


def show_warnings(**kwargs: Any) -> None:
    tail_logs(level="warning", **kwargs)


def search_logs(pattern: str, **kwargs: Any) -> None:
    tail_logs(search=pattern, **kwargs)


def _print_results(entries: list[dict[str, Any]], fmt: OutputFormat, jq_filter: str | None = None) -> None:
    payload = format_output(entries, fmt)

    if not jq_filter:
        print(payload)
        return

    try:
        runner = _jq_runner or _default_jq_runner
        result = runner(jq_filter, payload)

        if isinstance(result, subprocess.CompletedProcess):
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                if stderr:
                    print(f"jq exited with status {result.returncode}: {stderr}", file=sys.stderr)
                else:
                    print(f"jq exited with status {result.returncode}", file=sys.stderr)
                print(payload)
                return

            output = result.stdout or ""
            sys.stdout.write(output)
            if not output.endswith("\n"):
                sys.stdout.write("\n")
        else:
            # Custom test runner result
            if hasattr(result, "status") and result.status != 0:
                stderr = (getattr(result, "stderr", "") or "").strip()
                if stderr:
                    print(f"jq exited with status {result.status}: {stderr}", file=sys.stderr)
                else:
                    print(f"jq exited with status {result.status}", file=sys.stderr)
                print(payload)
                return
            output = getattr(result, "stdout", "") or ""
            sys.stdout.write(output)
            if not output.endswith("\n"):
                sys.stdout.write("\n")
    except FileNotFoundError:
        print("jq execution failed: jq not found in PATH", file=sys.stderr)
        print(payload)
    except Exception as e:
        print(f"jq integration error: {e}", file=sys.stderr)
        print(payload)


def _default_jq_runner(jq_filter: str, payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["jq", jq_filter],
        input=payload,
        capture_output=True,
        text=True,
    )
