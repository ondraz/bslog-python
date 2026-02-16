"""CLI entry point for bslog."""

from typing import Annotated

import typer

from bslog import __version__

app = typer.Typer(
    name="bslog",
    help="Better Stack log query CLI with GraphQL-inspired syntax",
    no_args_is_help=True,
)

sources_app = typer.Typer(help="Manage log sources")
config_app = typer.Typer(help="Manage configuration")
app.add_typer(sources_app, name="sources")
app.add_typer(config_app, name="config")


def version_callback(value: bool) -> None:
    if value:
        print(f"bslog {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Show version and exit", callback=version_callback, is_eager=True),
    ] = False,
) -> None:
    pass


@app.command()
def query(
    query_str: Annotated[str, typer.Argument(help="GraphQL-like query string")],
    source: Annotated[str | None, typer.Option("-s", "--source", help="Source name")] = None,
    fmt: Annotated[str, typer.Option("-f", "--format", help="Output format (json|table|csv|pretty)")] = "pretty",
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Show SQL query and debug information")] = False,
) -> None:
    """Query logs using GraphQL-like syntax."""
    from bslog.commands.query_cmd import run_query

    run_query(query_str, source=source, fmt=fmt, verbose=verbose)


@app.command()
def sql(
    sql_str: Annotated[str, typer.Argument(help="Raw ClickHouse SQL query")],
    fmt: Annotated[str, typer.Option("-f", "--format", help="Output format (json|table|csv|pretty)")] = "json",
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Show SQL query and debug information")] = False,
) -> None:
    """Execute raw ClickHouse SQL query."""
    from bslog.commands.query_cmd import run_sql

    run_sql(sql_str, fmt=fmt, verbose=verbose)


@app.command()
def tail(
    source: Annotated[str | None, typer.Argument(help="Source name or alias")] = None,
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of logs to fetch")] = 100,
    level: Annotated[str | None, typer.Option("-l", "--level", help="Filter by log level")] = None,
    subsystem: Annotated[str | None, typer.Option("--subsystem", help="Filter by subsystem")] = None,
    follow: Annotated[bool, typer.Option("-f", "--follow", help="Follow log output")] = False,
    interval: Annotated[int, typer.Option("--interval", help="Polling interval in milliseconds")] = 2000,
    since: Annotated[str | None, typer.Option("--since", help="Time lower bound (e.g., 1h, 2d, 2024-01-01)")] = None,
    until: Annotated[str | None, typer.Option("--until", help="Time upper bound")] = None,
    fmt: Annotated[str, typer.Option("--format", help="Output format (json|table|csv|pretty)")] = "pretty",
    fields: Annotated[str | None, typer.Option("--fields", help="Comma-separated list of fields")] = None,
    sources: Annotated[str | None, typer.Option("--sources", help="Comma-separated list of sources to merge")] = None,
    where: Annotated[list[str] | None, typer.Option("--where", help="Filter JSON fields (field=value)")] = None,
    jq: Annotated[str | None, typer.Option("--jq", help="Pipe JSON output through jq")] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Show SQL query and debug information")] = False,
) -> None:
    """Tail logs (similar to tail -f)."""
    from bslog.commands.tail import tail_logs
    from bslog.utils.options import normalize_sources_option, parse_where_option

    parsed_sources = normalize_sources_option(sources)
    parsed_where = parse_where_option(where)

    tail_logs(
        source=source,
        limit=limit,
        level=level,
        subsystem=subsystem,
        follow=follow,
        interval=interval,
        since=since,
        until=until,
        fmt=fmt,
        fields=fields,
        sources=parsed_sources,
        where=parsed_where,
        jq_filter=jq,
        verbose=verbose,
    )


@app.command()
def errors(
    source: Annotated[str | None, typer.Argument(help="Source name or alias")] = None,
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of logs to fetch")] = 100,
    since: Annotated[str | None, typer.Option("--since", help="Time lower bound")] = None,
    until: Annotated[str | None, typer.Option("--until", help="Time upper bound")] = None,
    fmt: Annotated[str, typer.Option("--format", help="Output format")] = "pretty",
    fields: Annotated[str | None, typer.Option("--fields", help="Comma-separated list of fields")] = None,
    sources: Annotated[str | None, typer.Option("--sources", help="Comma-separated sources to merge")] = None,
    where: Annotated[list[str] | None, typer.Option("--where", help="Filter JSON fields")] = None,
    jq: Annotated[str | None, typer.Option("--jq", help="Pipe through jq")] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Show SQL")] = False,
) -> None:
    """Show only error logs."""
    from bslog.commands.tail import show_errors
    from bslog.utils.options import normalize_sources_option, parse_where_option

    show_errors(
        source=source, limit=limit, since=since, until=until, fmt=fmt, fields=fields,
        sources=normalize_sources_option(sources), where=parse_where_option(where),
        jq_filter=jq, verbose=verbose,
    )


@app.command()
def warnings(
    source: Annotated[str | None, typer.Argument(help="Source name or alias")] = None,
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of logs to fetch")] = 100,
    since: Annotated[str | None, typer.Option("--since", help="Time lower bound")] = None,
    until: Annotated[str | None, typer.Option("--until", help="Time upper bound")] = None,
    fmt: Annotated[str, typer.Option("--format", help="Output format")] = "pretty",
    fields: Annotated[str | None, typer.Option("--fields", help="Comma-separated list of fields")] = None,
    sources: Annotated[str | None, typer.Option("--sources", help="Comma-separated sources to merge")] = None,
    where: Annotated[list[str] | None, typer.Option("--where", help="Filter JSON fields")] = None,
    jq: Annotated[str | None, typer.Option("--jq", help="Pipe through jq")] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Show SQL")] = False,
) -> None:
    """Show only warning logs."""
    from bslog.commands.tail import show_warnings
    from bslog.utils.options import normalize_sources_option, parse_where_option

    show_warnings(
        source=source, limit=limit, since=since, until=until, fmt=fmt, fields=fields,
        sources=normalize_sources_option(sources), where=parse_where_option(where),
        jq_filter=jq, verbose=verbose,
    )


@app.command()
def search(
    pattern: Annotated[str, typer.Argument(help="Substring or expression to search for")],
    source: Annotated[str | None, typer.Argument(help="Source name or alias")] = None,
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of logs to fetch")] = 100,
    level: Annotated[str | None, typer.Option("-l", "--level", help="Filter by log level")] = None,
    since: Annotated[str | None, typer.Option("--since", help="Time lower bound")] = None,
    until: Annotated[str | None, typer.Option("--until", help="Time upper bound")] = None,
    fmt: Annotated[str, typer.Option("--format", help="Output format")] = "pretty",
    fields: Annotated[str | None, typer.Option("--fields", help="Comma-separated list of fields")] = None,
    sources: Annotated[str | None, typer.Option("--sources", help="Comma-separated sources to merge")] = None,
    where: Annotated[list[str] | None, typer.Option("--where", help="Filter JSON fields")] = None,
    jq: Annotated[str | None, typer.Option("--jq", help="Pipe through jq")] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Show SQL")] = False,
) -> None:
    """Search logs for a pattern."""
    from bslog.commands.tail import search_logs
    from bslog.utils.options import normalize_sources_option, parse_where_option

    search_logs(
        pattern, source=source, limit=limit, level=level, since=since, until=until, fmt=fmt,
        fields=fields, sources=normalize_sources_option(sources), where=parse_where_option(where),
        jq_filter=jq, verbose=verbose,
    )


@app.command()
def trace(
    request_id: Annotated[str, typer.Argument(help="Request identifier to trace")],
    source: Annotated[str | None, typer.Argument(help="Source name or alias")] = None,
    limit: Annotated[int, typer.Option("-n", "--limit", help="Number of logs to fetch")] = 100,
    since: Annotated[str | None, typer.Option("--since", help="Time lower bound")] = None,
    until: Annotated[str | None, typer.Option("--until", help="Time upper bound")] = None,
    fmt: Annotated[str, typer.Option("--format", help="Output format")] = "pretty",
    fields: Annotated[str | None, typer.Option("--fields", help="Comma-separated list of fields")] = None,
    sources: Annotated[str | None, typer.Option("--sources", help="Comma-separated sources to merge")] = None,
    where: Annotated[list[str] | None, typer.Option("--where", help="Filter JSON fields")] = None,
    jq: Annotated[str | None, typer.Option("--jq", help="Pipe through jq")] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Show SQL")] = False,
) -> None:
    """Fetch all logs sharing a requestId across one or more sources."""
    from bslog.commands.trace import trace_request
    from bslog.utils.options import normalize_sources_option, parse_where_option

    trace_request(
        request_id, where=parse_where_option(where), source=source, limit=limit,
        since=since, until=until, fmt=fmt, fields=fields,
        sources=normalize_sources_option(sources), jq_filter=jq, verbose=verbose,
    )


# Sources subcommands
@sources_app.command("list")
def sources_list(
    fmt: Annotated[str, typer.Option("-f", "--format", help="Output format (json|table|pretty)")] = "pretty",
) -> None:
    """List all available sources."""
    from bslog.commands.sources import list_sources

    list_sources(fmt=fmt)


@sources_app.command("get")
def sources_get(
    name: Annotated[str, typer.Argument(help="Source name")],
    fmt: Annotated[str, typer.Option("-f", "--format", help="Output format (json|pretty)")] = "pretty",
) -> None:
    """Get details about a specific source."""
    from bslog.commands.sources import get_source

    get_source(name, fmt=fmt)


# Config subcommands
@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key (source|limit|format|logLevel|queryBaseUrl)")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
) -> None:
    """Set a configuration value."""
    from bslog.commands.config_cmd import set_config

    set_config(key, value)


@config_app.command("show")
def config_show(
    fmt: Annotated[str, typer.Option("-f", "--format", help="Output format (json|pretty)")] = "pretty",
) -> None:
    """Show current configuration."""
    from bslog.commands.config_cmd import show_config

    show_config(fmt=fmt)


@config_app.command("source")
def config_source(
    name: Annotated[str, typer.Argument(help="Source name")],
) -> None:
    """Set default source (shorthand for config set source)."""
    from bslog.commands.config_cmd import set_config

    set_config("source", name)
