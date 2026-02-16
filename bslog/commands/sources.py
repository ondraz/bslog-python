"""Sources command for listing and inspecting log sources."""

import sys

from rich.console import Console

from bslog.api.sources import SourcesAPI
from bslog.utils.formatter import format_bytes, format_output

console = Console()


def list_sources(fmt: str = "pretty") -> None:
    api = SourcesAPI()

    try:
        sources = api.list_all()

        if fmt in ("table", "pretty"):
            console.print("\n[bold]Available Sources:[/bold]\n")

            for source in sources:
                attrs = source.attributes
                messages = f"{attrs.messages_count:,}" if attrs.messages_count else "0"
                size = format_bytes(attrs.bytes_count or 0)
                status = "[red]Paused[/red]" if attrs.ingesting_paused else "[green]Active[/green]"

                console.print(f"  [cyan]{attrs.name}[/cyan]")
                console.print(f"    Platform: {attrs.platform}")
                console.print(f"    Messages: {messages}")
                console.print(f"    Size: {size}")
                console.print(f"    Status: {status}")
                console.print(f"    ID: {source.id}")
                console.print()
        else:
            data = [
                {
                    "id": s.id,
                    "type": s.type,
                    "name": s.attributes.name,
                    "platform": s.attributes.platform,
                    "messages_count": s.attributes.messages_count,
                    "bytes_count": s.attributes.bytes_count,
                    "ingesting_paused": s.attributes.ingesting_paused,
                }
                for s in sources
            ]
            output = format_output(data, fmt)
            print(output)
    except Exception as e:
        console.print(f"[red]Error listing sources: {e}[/red]")
        sys.exit(1)


def get_source(name: str, fmt: str = "pretty") -> None:
    api = SourcesAPI()

    try:
        source = api.find_by_name(name)

        if not source:
            console.print(f"[red]Source not found: {name}[/red]")
            sys.exit(1)

        if fmt == "pretty":
            attrs = source.attributes

            console.print(f"\n[bold]Source: {attrs.name}[/bold]\n")
            console.print(f"ID: {source.id}")
            console.print(f"Platform: {attrs.platform}")
            token_display = f"{attrs.token[:10]}..." if attrs.token else "N/A"
            console.print(f"Token: {token_display}")
            messages = f"{attrs.messages_count:,}" if attrs.messages_count else "0"
            console.print(f"Messages: {messages}")
            console.print(f"Size: {format_bytes(attrs.bytes_count or 0)}")
            status = "[red]Paused[/red]" if attrs.ingesting_paused else "[green]Active[/green]"
            console.print(f"Status: {status}")
            console.print(f"Created: {attrs.created_at or 'N/A'}")
            console.print(f"Updated: {attrs.updated_at or 'N/A'}")
        else:
            data = {
                "id": source.id,
                "type": source.type,
                "attributes": {
                    "name": source.attributes.name,
                    "platform": source.attributes.platform,
                    "token": source.attributes.token,
                    "team_id": source.attributes.team_id,
                    "table_name": source.attributes.table_name,
                    "messages_count": source.attributes.messages_count,
                    "bytes_count": source.attributes.bytes_count,
                    "ingesting_paused": source.attributes.ingesting_paused,
                },
            }
            output = format_output([data], fmt)
            print(output)
    except Exception as e:
        console.print(f"[red]Error getting source: {e}[/red]")
        sys.exit(1)
