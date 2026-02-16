"""CLI entry point for bslog."""

import click
import typer

from bslog import __version__

EPILOG = """\
Examples:

  # GraphQL-like queries:
  $ bslog query "{ logs(limit: 100) { dt, level, message } }"
  $ bslog query "{ logs(level: 'error', since: '1h') { * } }"
  $ bslog query "{ logs(where: { subsystem: 'api' }) { dt, message } }"

  # Simple commands:
  $ bslog tail -n 50                    # Last 50 logs
  $ bslog tail -f                       # Follow logs
  $ bslog errors --since 1h             # Errors from last hour
  $ bslog search "authentication failed"
  $ bslog search "timeline" --where module=timeline --where env=production --until 2025-09-24T18:00
  $ bslog tail --format json --jq '.[] | {dt, message}'

  # Sources:
  $ bslog sources list                  # List all sources
  $ bslog config source sweetistics-dev # Set default source

  # Raw SQL:
  $ bslog sql "SELECT * FROM remote(t123_logs) LIMIT 10"

Authentication:
  Requires environment variables for Better Stack API access:
  - BETTERSTACK_API_TOKEN        # For sources discovery
  - BETTERSTACK_QUERY_USERNAME   # For log queries
  - BETTERSTACK_QUERY_PASSWORD   # For log queries

  Add to ~/.zshrc (or ~/.bashrc) then reload with:
  $ source ~/.zshrc
"""


class EpilogGroup(typer.core.TyperGroup):
    """Custom group that preserves epilog formatting."""

    def get_help(self, ctx: click.Context) -> str:
        # Get Typer's Rich-formatted help (which mangles the epilog)
        # Temporarily remove epilog so Rich doesn't touch it
        epilog = self.epilog
        self.epilog = None
        help_text = super().get_help(ctx)
        self.epilog = epilog
        # Append raw epilog ourselves
        if epilog:
            help_text += "\n\n" + epilog
        return help_text


app = typer.Typer(
    name="bslog",
    help="Better Stack log query CLI with GraphQL-inspired syntax",
    invoke_without_command=True,
    cls=EpilogGroup,
)

sources_app = typer.Typer(help="Manage log sources")
config_app = typer.Typer(help="Manage configuration")
app.add_typer(sources_app, name="sources")
app.add_typer(config_app, name="config")


def version_callback(value: bool) -> None:
    if value:
        print(f"bslog {__version__}")
        raise typer.Exit()


@app.callback(epilog=EPILOG, invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Better Stack log query CLI with GraphQL-inspired syntax"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def query(
    query_str: str = typer.Argument(help="GraphQL-like query string"),
    source: str | None = typer.Option(None, "-s", "--source", help="Source name"),
    fmt: str = typer.Option("pretty", "-f", "--format", help="Output format (json|table|csv|pretty)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show SQL query and debug information"),
) -> None:
    """Query logs using GraphQL-like syntax."""
    from bslog.commands.query_cmd import run_query

    run_query(query_str, source=source, fmt=fmt, verbose=verbose)


@app.command()
def sql(
    sql_str: str = typer.Argument(help="Raw ClickHouse SQL query"),
    fmt: str = typer.Option("json", "-f", "--format", help="Output format (json|table|csv|pretty)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show SQL query and debug information"),
) -> None:
    """Execute raw ClickHouse SQL query."""
    from bslog.commands.query_cmd import run_sql

    run_sql(sql_str, fmt=fmt, verbose=verbose)


@app.command()
def tail(
    source: str | None = typer.Argument(None, help="Source name or alias"),
    limit: int = typer.Option(100, "-n", "--limit", help="Number of logs to fetch"),
    level: str | None = typer.Option(None, "-l", "--level", help="Filter by log level"),
    subsystem: str | None = typer.Option(None, "--subsystem", help="Filter by subsystem"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output"),
    interval: int = typer.Option(2000, "--interval", help="Polling interval in milliseconds"),
    since: str | None = typer.Option(None, "--since", help="Time lower bound (e.g., 1h, 2d, 2024-01-01)"),
    until: str | None = typer.Option(None, "--until", help="Time upper bound"),
    fmt: str = typer.Option("pretty", "--format", help="Output format (json|table|csv|pretty)"),
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated list of fields"),
    sources: str | None = typer.Option(None, "--sources", help="Comma-separated list of sources to merge"),
    where: list[str] | None = typer.Option(None, "--where", help="Filter JSON fields (field=value)"),
    jq: str | None = typer.Option(None, "--jq", help="Pipe JSON output through jq"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show SQL query and debug information"),
) -> None:
    """Tail logs (similar to tail -f).

    Examples:
      bslog tail                    # use default source
      bslog tail sweetistics-dev    # use specific source
      bslog tail prod -n 50         # tail production logs
    """
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
    source: str | None = typer.Argument(None, help="Source name or alias"),
    limit: int = typer.Option(100, "-n", "--limit", help="Number of logs to fetch"),
    since: str | None = typer.Option(None, "--since", help="Time lower bound"),
    until: str | None = typer.Option(None, "--until", help="Time upper bound"),
    fmt: str = typer.Option("pretty", "--format", help="Output format"),
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated list of fields"),
    sources: str | None = typer.Option(None, "--sources", help="Comma-separated sources to merge"),
    where: list[str] | None = typer.Option(None, "--where", help="Filter JSON fields"),
    jq: str | None = typer.Option(None, "--jq", help="Pipe through jq"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show SQL"),
) -> None:
    """Show only error logs.

    Examples:
      bslog errors                  # use default source
      bslog errors sweetistics-dev  # errors from dev
      bslog errors prod --since 1h  # recent prod errors
    """
    from bslog.commands.tail import show_errors
    from bslog.utils.options import normalize_sources_option, parse_where_option

    show_errors(
        source=source,
        limit=limit,
        since=since,
        until=until,
        fmt=fmt,
        fields=fields,
        sources=normalize_sources_option(sources),
        where=parse_where_option(where),
        jq_filter=jq,
        verbose=verbose,
    )


@app.command()
def warnings(
    source: str | None = typer.Argument(None, help="Source name or alias"),
    limit: int = typer.Option(100, "-n", "--limit", help="Number of logs to fetch"),
    since: str | None = typer.Option(None, "--since", help="Time lower bound"),
    until: str | None = typer.Option(None, "--until", help="Time upper bound"),
    fmt: str = typer.Option("pretty", "--format", help="Output format"),
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated list of fields"),
    sources: str | None = typer.Option(None, "--sources", help="Comma-separated sources to merge"),
    where: list[str] | None = typer.Option(None, "--where", help="Filter JSON fields"),
    jq: str | None = typer.Option(None, "--jq", help="Pipe through jq"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show SQL"),
) -> None:
    """Show only warning logs."""
    from bslog.commands.tail import show_warnings
    from bslog.utils.options import normalize_sources_option, parse_where_option

    show_warnings(
        source=source,
        limit=limit,
        since=since,
        until=until,
        fmt=fmt,
        fields=fields,
        sources=normalize_sources_option(sources),
        where=parse_where_option(where),
        jq_filter=jq,
        verbose=verbose,
    )


@app.command()
def search(
    pattern: str = typer.Argument(help="Substring or expression to search for"),
    source: str | None = typer.Argument(None, help="Source name or alias"),
    limit: int = typer.Option(100, "-n", "--limit", help="Number of logs to fetch"),
    level: str | None = typer.Option(None, "-l", "--level", help="Filter by log level"),
    since: str | None = typer.Option(None, "--since", help="Time lower bound"),
    until: str | None = typer.Option(None, "--until", help="Time upper bound"),
    fmt: str = typer.Option("pretty", "--format", help="Output format"),
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated list of fields"),
    sources: str | None = typer.Option(None, "--sources", help="Comma-separated sources to merge"),
    where: list[str] | None = typer.Option(None, "--where", help="Filter JSON fields"),
    jq: str | None = typer.Option(None, "--jq", help="Pipe through jq"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show SQL"),
) -> None:
    """Search logs for a pattern.

    Examples:
      bslog search "error"                    # search in default source
      bslog search "error" sweetistics-dev    # search in dev
      bslog search "timeout" prod --since 1h  # search recent prod logs
    """
    from bslog.commands.tail import search_logs
    from bslog.utils.options import normalize_sources_option, parse_where_option

    search_logs(
        pattern,
        source=source,
        limit=limit,
        level=level,
        since=since,
        until=until,
        fmt=fmt,
        fields=fields,
        sources=normalize_sources_option(sources),
        where=parse_where_option(where),
        jq_filter=jq,
        verbose=verbose,
    )


@app.command()
def trace(
    request_id: str = typer.Argument(help="Request identifier to trace"),
    source: str | None = typer.Argument(None, help="Source name or alias"),
    limit: int = typer.Option(100, "-n", "--limit", help="Number of logs to fetch"),
    since: str | None = typer.Option(None, "--since", help="Time lower bound"),
    until: str | None = typer.Option(None, "--until", help="Time upper bound"),
    fmt: str = typer.Option("pretty", "--format", help="Output format"),
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated list of fields"),
    sources: str | None = typer.Option(None, "--sources", help="Comma-separated sources to merge"),
    where: list[str] | None = typer.Option(None, "--where", help="Filter JSON fields"),
    jq: str | None = typer.Option(None, "--jq", help="Pipe through jq"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show SQL"),
) -> None:
    """Fetch all logs sharing a requestId across one or more sources."""
    from bslog.commands.trace import trace_request
    from bslog.utils.options import normalize_sources_option, parse_where_option

    trace_request(
        request_id,
        where=parse_where_option(where),
        source=source,
        limit=limit,
        since=since,
        until=until,
        fmt=fmt,
        fields=fields,
        sources=normalize_sources_option(sources),
        jq_filter=jq,
        verbose=verbose,
    )


# Sources subcommands
@sources_app.command("list")
def sources_list(
    fmt: str = typer.Option("pretty", "-f", "--format", help="Output format (json|table|pretty)"),
) -> None:
    """List all available sources."""
    from bslog.commands.sources import list_sources

    list_sources(fmt=fmt)


@sources_app.command("get")
def sources_get(
    name: str = typer.Argument(help="Source name"),
    fmt: str = typer.Option("pretty", "-f", "--format", help="Output format (json|pretty)"),
) -> None:
    """Get details about a specific source."""
    from bslog.commands.sources import get_source

    get_source(name, fmt=fmt)


# Config subcommands
@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Configuration key (source|limit|format|logLevel|queryBaseUrl)"),
    value: str = typer.Argument(help="Configuration value"),
) -> None:
    """Set a configuration value."""
    from bslog.commands.config_cmd import set_config

    set_config(key, value)


@config_app.command("show")
def config_show(
    fmt: str = typer.Option("pretty", "-f", "--format", help="Output format (json|pretty)"),
) -> None:
    """Show current configuration."""
    from bslog.commands.config_cmd import show_config

    show_config(fmt=fmt)


@config_app.command("source")
def config_source(
    name: str = typer.Argument(help="Source name"),
) -> None:
    """Set default source (shorthand for config set source)."""
    from bslog.commands.config_cmd import set_config

    set_config("source", name)
