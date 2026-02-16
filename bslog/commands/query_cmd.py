"""Query command for GraphQL and SQL queries."""

import sys

from rich.console import Console

from bslog.api.query import QueryAPI
from bslog.parser.graphql import parse_graphql_query
from bslog.utils.config import add_to_history
from bslog.utils.formatter import format_output

console = Console(stderr=True)


def run_query(query_str: str, source: str | None = None, fmt: str = "pretty", verbose: bool = False) -> None:
    api = QueryAPI()

    try:
        query_options = parse_graphql_query(query_str)

        if source:
            query_options.source = source
        if verbose:
            query_options.verbose = True

        add_to_history(query_str)

        results = api.execute(query_options)

        output = format_output(results, fmt)
        print(output)

        if not results:
            console.print("[yellow]\nNo results found[/yellow]")
        else:
            console.print(f"[dim]\n{len(results)} results returned[/dim]")
    except Exception as e:
        console.print(f"[red]Query error: {e}[/red]")
        sys.exit(1)


def run_sql(sql: str, fmt: str = "json", verbose: bool = False) -> None:
    api = QueryAPI()

    try:
        add_to_history(f"SQL: {sql}")

        if verbose:
            print(f"Executing: {sql}", file=sys.stderr)

        results = api.execute_sql(sql)

        output = format_output(results, fmt)
        print(output)

        if not results:
            console.print("[yellow]\nNo results found[/yellow]")
        else:
            console.print(f"[dim]\n{len(results)} results returned[/dim]")
    except Exception as e:
        console.print(f"[red]SQL error: {e}[/red]")
        sys.exit(1)
