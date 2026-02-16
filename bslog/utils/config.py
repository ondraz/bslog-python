"""Configuration management for bslog."""

import json
import os
import warnings
from pathlib import Path

from bslog.types import Config

CONFIG_DIR = Path.home() / ".bslog"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_QUERY_BASE_URL = "https://eu-nbg-2-connect.betterstackdata.com"

SOURCE_ALIASES: dict[str, str] = {
    "dev": "sweetistics-dev",
    "development": "sweetistics-dev",
    "prod": "sweetistics",
    "production": "sweetistics",
    "staging": "sweetistics-staging",
    "test": "sweetistics-test",
}


def get_api_token() -> str:
    token = os.environ.get("BETTERSTACK_API_TOKEN")
    if not token:
        raise RuntimeError(
            "BETTERSTACK_API_TOKEN environment variable is not set.\n"
            "Please add it to your shell configuration:\n"
            'export BETTERSTACK_API_TOKEN="your_token_here"'
        )
    return token


def get_query_credentials() -> dict[str, str | None]:
    username = os.environ.get("BETTERSTACK_QUERY_USERNAME")
    password = os.environ.get("BETTERSTACK_QUERY_PASSWORD")
    return {"username": username, "password": password}


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        return Config(
            defaultLimit=100,
            outputFormat="json",
            defaultLogLevel="all",
            queryHistory=[],
            savedQueries={},
        )

    try:
        content = CONFIG_FILE.read_text(encoding="utf-8")
        data = json.loads(content)

        config = Config(
            defaultSource=data.get("defaultSource"),
            defaultLimit=data.get("defaultLimit", 100),
            outputFormat=data.get("outputFormat", "json"),
            defaultLogLevel=data.get("defaultLogLevel", "all"),
            queryBaseUrl=data.get("queryBaseUrl"),
            queryHistory=data.get("queryHistory", []),
            savedQueries=data.get("savedQueries", {}),
        )

        if not config.defaultLogLevel:
            config.defaultLogLevel = "all"

        return config
    except Exception:
        warnings.warn("Failed to load config, using defaults", stacklevel=2)
        return Config(
            defaultLimit=100,
            outputFormat="json",
            defaultLogLevel="all",
        )


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        k: v
        for k, v in {
            "defaultSource": config.defaultSource,
            "defaultLimit": config.defaultLimit,
            "outputFormat": config.outputFormat,
            "defaultLogLevel": config.defaultLogLevel,
            "queryBaseUrl": config.queryBaseUrl,
            "queryHistory": config.queryHistory,
            "savedQueries": config.savedQueries,
        }.items()
        if v is not None
    }

    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_config(updates: dict) -> None:  # type: ignore[type-arg]
    config = load_config()
    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)
    save_config(config)


def add_to_history(query: str) -> None:
    config = load_config()
    history = config.queryHistory or []

    history.insert(0, query)
    if len(history) > 100:
        history.pop()

    update_config({"queryHistory": history})


def resolve_source_alias(source: str | None) -> str | None:
    if source is None:
        return None

    aliased = SOURCE_ALIASES.get(source.lower())
    if aliased:
        return aliased

    return source
