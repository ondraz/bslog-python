# bslog - Better Stack Log CLI

[![PyPI version](https://img.shields.io/pypi/v/bslog.svg)](https://pypi.org/project/bslog/)
[![Python version](https://img.shields.io/badge/python-%3E%3D3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful, intuitive CLI tool for querying Better Stack logs with GraphQL-inspired syntax. Query your logs naturally without memorizing complex SQL or API endpoints.

This is python adaptation of original typescript [bslog](https://github.com/steipete/bslog) from @steipete.

## Features

- **GraphQL-inspired query syntax** - Write queries that feel natural and are easy to remember
- **Simple commands** - Common operations like `tail`, `errors`, `search` work out of the box
- **Smart filtering** - Filter by level, subsystem, time ranges, or any JSON field
- **Beautiful output** - Color-coded, formatted logs that are easy to read
- **Multiple formats** - Export as JSON, CSV, or formatted tables
- **Real-time following** - Tail logs in real-time with `-f` flag
- **Query history** - Saves your queries for quick re-use
- **Configurable** - Set defaults for source, output format, and more
- **jq integration** - Pipe output through jq for advanced filtering

## Installation

### From PyPI (Recommended)

```bash
pip install bslog

# Or with uv
uv add bslog
```

### From Source

```bash
git clone <repo-url>
cd bslog-python
uv sync
```

### Prerequisites

- **Python** >= 3.13

## Authentication Setup

Better Stack uses two different authentication systems, and **both are required** for full functionality:

### 1. Telemetry API Token (Required)

Used for listing sources, getting source metadata, and resolving source names.

1. Log into [Better Stack](https://betterstack.com)
2. Navigate to **Settings > API Tokens**
3. Create or copy your **Telemetry API token**
4. Add to your shell configuration:

```bash
export BETTERSTACK_API_TOKEN="your_telemetry_token_here"
```

### 2. Query API Credentials (Required for querying logs)

Used for reading log data and executing SQL queries.

1. Go to Better Stack > **Logs > Dashboards**
2. Click **"Connect remotely"**
3. Click **"Create credentials"**
4. Add to your shell configuration:

```bash
export BETTERSTACK_QUERY_USERNAME="your_username_here"
export BETTERSTACK_QUERY_PASSWORD="your_password_here"
```

Then reload your shell: `source ~/.zshrc`

## Quick Start

```bash
# List all your log sources
bslog sources list

# Set your default source
bslog config source my-app-production

# Get last 100 logs
bslog tail

# Get last 50 error logs
bslog errors -n 50

# Search for specific text
bslog search "user authentication failed"

# Follow logs in real-time
bslog tail -f

# Get logs from the last hour
bslog tail --since 1h
```

## GraphQL-Inspired Query Syntax

```bash
# Simple query with field selection
bslog query "{ logs(limit: 100) { dt, level, message } }"

# Filter by log level
bslog query "{ logs(level: 'error', limit: 50) { * } }"

# Time-based filtering
bslog query "{ logs(since: '1h') { dt, message, error } }"

# Complex filters
bslog query "{
  logs(
    level: 'error',
    subsystem: 'payment',
    since: '1h',
    limit: 200,
    where: { environment: 'prod' }
  ) {
    dt, message, userId
  }
}"
```

## Command Reference

### `tail` - Stream logs
```bash
bslog tail [source] [options]
  -n, --limit <number>    Number of logs (default: 100)
  -l, --level <level>     Filter by log level
  --subsystem <name>      Filter by subsystem
  -f, --follow            Follow log output
  --interval <ms>         Polling interval (default: 2000)
  --since <time>          Time lower bound (e.g., 1h, 2d)
  --until <time>          Time upper bound
  --format <type>         Output format (json|table|csv|pretty)
  --fields <names>        Comma-separated list of fields
  --sources <names>       Comma-separated sources to merge
  --where <filter>        Filter JSON fields (field=value, repeatable)
  --jq <filter>           Pipe JSON through jq
  -v, --verbose           Show SQL query
```

### `errors` / `warnings` - Show error/warning logs
```bash
bslog errors [source] [options]   # Same options as tail
bslog warnings [source] [options]
```

### `search` - Search logs
```bash
bslog search <pattern> [source] [options]
```

### `trace` - Follow a request across sources
```bash
bslog trace <requestId> [source] [options]
```

### `query` - GraphQL-inspired queries
```bash
bslog query <query> [-s source] [-f format] [-v]
```

### `sql` - Raw ClickHouse SQL
```bash
bslog sql <sql> [-f format] [-v]
```

### `sources list` / `sources get`
```bash
bslog sources list [-f format]
bslog sources get <name> [-f format]
```

### `config set` / `config show` / `config source`
```bash
bslog config set <key> <value>     # Keys: source, limit, format, logLevel, queryBaseUrl
bslog config show [-f format]
bslog config source <name>         # Shorthand for config set source
```

## Source Aliases

- `dev`, `development` → `sweetistics-dev`
- `prod`, `production` → `sweetistics`
- `staging` → `sweetistics-staging`
- `test` → `sweetistics-test`

## Time Format Reference

- **Relative**: `1h`, `30m`, `2d`, `1w`
- **ISO 8601**: `2024-01-15T10:30:00Z`
- **Date only**: `2024-01-15`

## Output Formats

- **`pretty`** - Color-coded human-readable output (default)
- **`json`** - Standard JSON, good for piping
- **`table`** - Formatted table output
- **`csv`** - CSV for spreadsheet import

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest --cov=bslog -v

# Lint
uv run ruff check .

# Type check
uv run mypy bslog
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

This is python adaptation of original typescript [bslog](https://github.com/steipete/bslog) from @steipete.

- Built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)
- HTTP client: [httpx](https://www.python-httpx.org/)
- Powered by [Better Stack](https://betterstack.com) logging infrastructure
- Inspired by GraphQL's intuitive query syntax
