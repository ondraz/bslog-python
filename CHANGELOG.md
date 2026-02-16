# Changelog

## [1.4.0] - 2026-02-16
- Rewritten from TypeScript/Bun to Python 3.13.
- CLI powered by Typer with Rich for formatted output.
- HTTP client using httpx instead of native Fetch API.
- Package management with UV and hatchling build system.
- Tests ported to pytest with full coverage.
- Published to PyPI as `bslog` (previously `@steipete/bslog` on npm).
- All features preserved: GraphQL queries, tail/errors/warnings/search/trace, multi-source correlation, follow mode, jq integration, 4 output formats.
