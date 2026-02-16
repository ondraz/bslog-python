"""Configuration management commands."""

import json
import sys

from rich.console import Console

from bslog.utils.config import DEFAULT_QUERY_BASE_URL, load_config, update_config

console = Console()

VALID_FORMATS = ("json", "table", "csv", "pretty")
VALID_LEVELS = {"all", "debug", "info", "warning", "error", "fatal", "trace"}
LEVEL_ALIASES = {"warn": "warning"}


def set_config(key: str, value: str) -> None:
    valid_keys = ["source", "limit", "format", "logLevel", "queryBaseUrl"]

    if key not in valid_keys:
        console.print(f"[red]Invalid config key: {key}[/red]")
        console.print(f"Valid keys: {', '.join(valid_keys)}")
        sys.exit(1)

    if key == "source":
        update_config({"defaultSource": value})
        console.print(f"[green]Default source set to: {value}[/green]")

    elif key == "limit":
        try:
            limit = int(value)
            if limit < 1:
                raise ValueError
        except ValueError:
            console.print("[red]Limit must be a positive number[/red]")
            sys.exit(1)
        update_config({"defaultLimit": limit})
        console.print(f"[green]Default limit set to: {limit}[/green]")

    elif key == "format":
        if value not in VALID_FORMATS:
            console.print(f"[red]Invalid format: {value}[/red]")
            console.print(f"Valid formats: {', '.join(VALID_FORMATS)}")
            sys.exit(1)
        update_config({"outputFormat": value})
        console.print(f"[green]Default output format set to: {value}[/green]")

    elif key == "logLevel":
        normalized = value.strip().lower()
        resolved = LEVEL_ALIASES.get(normalized, normalized)

        if resolved not in VALID_LEVELS:
            console.print(f"[red]Invalid log level: {value}[/red]")
            console.print(f"Valid levels: {', '.join(sorted(VALID_LEVELS))}")
            sys.exit(1)

        update_config({"defaultLogLevel": resolved})
        console.print(f"[green]Default log level set to: {resolved}[/green]")

    elif key == "queryBaseUrl":
        if not value.startswith("http://") and not value.startswith("https://"):
            console.print("[red]queryBaseUrl must start with http:// or https://[/red]")
            sys.exit(1)
        update_config({"queryBaseUrl": value})
        console.print(f"[green]Query base URL set to: {value}[/green]")


def show_config(fmt: str = "pretty") -> None:
    config = load_config()

    if fmt == "json":
        normalized = {
            "defaultSource": config.defaultSource,
            "defaultLimit": config.defaultLimit or 100,
            "defaultLogLevel": config.defaultLogLevel or "all",
            "outputFormat": config.outputFormat or "json",
            "queryBaseUrl": config.queryBaseUrl or DEFAULT_QUERY_BASE_URL,
            "savedQueries": config.savedQueries or {},
            "queryHistory": config.queryHistory or [],
        }
        print(json.dumps(normalized, indent=2))
        return

    console.print("\n[bold]Current Configuration:[/bold]\n")
    console.print(f"Default Source: {config.defaultSource or '[dim](not set)[/dim]'}")
    console.print(f"Default Limit: {config.defaultLimit or 100}")
    console.print(f"Default Log Level: {config.defaultLogLevel or 'all'}")
    console.print(f"Output Format: {config.outputFormat or 'json'}")
    console.print(f"Query Base URL: {config.queryBaseUrl or DEFAULT_QUERY_BASE_URL}")

    if config.savedQueries:
        console.print("\n[bold]Saved Queries:[/bold]")
        for name, query in config.savedQueries.items():
            console.print(f"  [cyan]{name}[/cyan]: {query}")

    console.print()
