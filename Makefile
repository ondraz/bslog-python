install:        ## Install bslog
	uv sync --no-dev

install-dev:    ## Install bslog with all dev dependencies
	uv sync
	uv run pre-commit install

check:          ## Run tests, ruff, and mypy
	uv run pytest --cov=bslog -v
	uv run ruff check .
	uv run mypy bslog
