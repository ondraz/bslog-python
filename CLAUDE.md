# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Building and Running
```bash
# Install with dev dependencies
uv sync

# Install production only
uv sync --no-dev

# Run the CLI
uv run bslog --help
```

### Testing
```bash
# Run all tests
uv run pytest --cov=bslog -v

# Run unit tests only
uv run pytest tests/unit/ -v

# Run integration tests only
uv run pytest tests/integration/ -v

# Run with coverage report
uv run pytest --cov=bslog --cov-report=term-missing
```

### Code Quality
```bash
# Linting
uv run ruff check .

# Type checking
uv run mypy bslog

# All checks (tests + lint + types)
make check
```

## Architecture Overview

### Core Structure
The application is a CLI tool built with Python 3.13 and Typer that provides a GraphQL-inspired query interface for Better Stack logs.

**Key architectural decisions:**
- **Typer** for CLI command parsing with Rich for terminal output
- **httpx** for HTTP client with timeout handling
- **Dual authentication**: Telemetry API token (source discovery) and Query API credentials (log data access)
- **GraphQL-inspired syntax**: Custom parser in `bslog/parser/graphql.py` converts user-friendly queries to ClickHouse SQL
- **Source aliases**: Built-in aliases for common environments (dev→sweetistics-dev, prod→sweetistics, etc.)

### Directory Layout
```
bslog/
├── __init__.py        # Package init with version and dotenv loading
├── cli.py             # Typer CLI entry point
├── types.py           # Dataclass type definitions
├── api/               # API clients for Better Stack
│   ├── client.py      # HTTP client wrapper (httpx)
│   ├── query.py       # Query API for log data (ClickHouse SQL builder)
│   └── sources.py     # Sources API for metadata
├── commands/          # CLI command implementations
│   ├── config_cmd.py  # Configuration management
│   ├── query_cmd.py   # GraphQL and SQL query handlers
│   ├── sources.py     # Source listing and details
│   ├── tail.py        # Log streaming (tail, errors, warnings, search)
│   └── trace.py       # Request tracing across sources
├── parser/
│   └── graphql.py     # GraphQL-to-SQL converter
└── utils/
    ├── config.py      # Config file management (~/.bslog/config.json)
    ├── formatter.py   # Output formatting (pretty, json, table, csv)
    ├── options.py     # CLI option parsing and normalization
    └── time.py        # Time parsing and conversion
```

### Authentication Flow
1. **Telemetry API** (`BETTERSTACK_API_TOKEN`): Used by `SourcesAPI` to discover available log sources
2. **Query API** (`BETTERSTACK_QUERY_USERNAME/PASSWORD`): Used by `QueryAPI` to execute ClickHouse SQL queries

### Query Processing Pipeline
1. User provides GraphQL-like query or uses convenience commands (tail, errors, etc.)
2. `parse_graphql_query()` converts GraphQL syntax to `QueryOptions` dataclass
3. `QueryAPI.build_query()` constructs ClickHouse SQL
4. Query executed via httpx POST to Better Stack's ClickHouse endpoint
5. Results formatted based on output format (pretty, json, table, csv)

## Testing Strategy

- **Unit tests** (`tests/unit/`): Test utilities, parsers, formatters, config, and option parsing
- **Integration tests** (`tests/integration/`): Test query building and SQL generation
- Tests use `unittest.mock` for mocking API calls and config file I/O
- Use `tmp_path` fixture for config file tests
- All tests must pass before commit

## Code Style

- **Linter**: Ruff with UP (pyupgrade), I (isort), E, F, N, W rules
- **Line length**: 120 characters
- **Type annotations**: Required on all function definitions (mypy strict)
- **Python version**: 3.13+ (uses modern union syntax `X | Y`)
