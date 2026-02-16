"""Tests for configuration utilities."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import bslog.utils.config as config_module
from bslog.types import Config
from bslog.utils.config import (
    DEFAULT_QUERY_BASE_URL,
    add_to_history,
    get_api_token,
    get_query_credentials,
    load_config,
    resolve_source_alias,
    save_config,
    update_config,
)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Use a temporary directory for config tests."""
    cfg_dir = tmp_path / ".bslog"
    cfg_dir.mkdir()
    return cfg_dir


@pytest.fixture(autouse=True)
def _patch_config_paths(config_dir: Path) -> None:
    """Redirect config paths to temp directory for all tests."""
    with patch.object(config_module, "CONFIG_DIR", config_dir), \
         patch.object(config_module, "CONFIG_FILE", config_dir / "config.json"):
        yield


class TestLoadConfig:
    def test_return_default_config_when_file_does_not_exist(self) -> None:
        config = load_config()

        assert config.defaultLimit == 100
        assert config.outputFormat == "json"
        assert config.defaultLogLevel == "all"
        assert config.queryHistory == []
        assert config.savedQueries == {}

    def test_no_queryBaseUrl_in_defaults(self) -> None:  # noqa: N802
        config = load_config()
        assert config.queryBaseUrl is None
        assert DEFAULT_QUERY_BASE_URL == "https://eu-nbg-2-connect.betterstackdata.com"

    def test_load_existing_config_from_file(self, config_dir: Path) -> None:
        test_config = Config(
            defaultSource="test-source",
            defaultLimit=200,
            outputFormat="pretty",
            queryHistory=["test query"],
            savedQueries={"test": "query"},
            defaultLogLevel="warning",
        )
        save_config(test_config)
        loaded = load_config()

        assert loaded.defaultSource == "test-source"
        assert loaded.defaultLimit == 200
        assert loaded.outputFormat == "pretty"
        assert loaded.queryHistory == ["test query"]
        assert loaded.savedQueries == {"test": "query"}
        assert loaded.defaultLogLevel == "warning"


class TestSaveConfig:
    def test_create_config_directory(self, config_dir: Path) -> None:
        import shutil
        shutil.rmtree(config_dir, ignore_errors=True)

        config = Config(defaultLimit=150, outputFormat="json")
        save_config(config)

        assert config_dir.exists()
        assert (config_dir / "config.json").exists()

    def test_save_config_as_formatted_json(self, config_dir: Path) -> None:
        config = Config(
            defaultSource="production",
            defaultLimit=100,
            outputFormat="pretty",
        )
        save_config(config)

        content = (config_dir / "config.json").read_text()
        parsed = json.loads(content)

        assert parsed["defaultSource"] == "production"
        assert "\n" in content


class TestUpdateConfig:
    def test_merge_updates_with_existing_config(self) -> None:
        initial = Config(
            defaultSource="dev",
            defaultLimit=100,
            outputFormat="json",
        )
        save_config(initial)

        update_config({"defaultLimit": 200, "outputFormat": "pretty"})

        result = load_config()
        assert result.defaultSource == "dev"
        assert result.defaultLimit == 200
        assert result.outputFormat == "pretty"

    def test_round_trip_custom_queryBaseUrl(self) -> None:  # noqa: N802
        initial = Config(defaultLimit=100, outputFormat="json")
        save_config(initial)

        update_config({"queryBaseUrl": "https://custom-connect.example.com"})

        result = load_config()
        assert result.queryBaseUrl == "https://custom-connect.example.com"
        assert result.defaultLimit == 100

    def test_add_new_properties(self) -> None:
        initial = Config(defaultLimit=100, outputFormat="json")
        save_config(initial)

        update_config({"defaultSource": "new-source"})

        result = load_config()
        assert result.defaultSource == "new-source"
        assert result.defaultLimit == 100


class TestAddToHistory:
    def test_add_query_to_beginning_of_history(self) -> None:
        save_config(Config(
            defaultLimit=100,
            outputFormat="json",
            queryHistory=["old query"],
        ))

        add_to_history("new query")

        config = load_config()
        assert config.queryHistory == ["new query", "old query"]

    def test_limit_history_to_100_entries(self) -> None:
        history = [f"query {i}" for i in range(100)]
        save_config(Config(
            defaultLimit=100,
            outputFormat="json",
            queryHistory=history,
        ))

        add_to_history("new query")

        config = load_config()
        assert len(config.queryHistory) == 100
        assert config.queryHistory[0] == "new query"
        assert config.queryHistory[99] == "query 98"

    def test_create_history_array_if_not_exists(self) -> None:
        save_config(Config(defaultLimit=100, outputFormat="json"))

        add_to_history("first query")

        config = load_config()
        assert config.queryHistory == ["first query"]


class TestGetApiToken:
    def test_throw_error_when_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("BETTERSTACK_API_TOKEN", None)
            with pytest.raises(RuntimeError, match="BETTERSTACK_API_TOKEN environment variable is not set"):
                get_api_token()

    def test_return_token_when_set(self) -> None:
        with patch.dict(os.environ, {"BETTERSTACK_API_TOKEN": "test_token_123"}):
            assert get_api_token() == "test_token_123"


class TestGetQueryCredentials:
    def test_return_none_when_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("BETTERSTACK_QUERY_USERNAME", None)
            os.environ.pop("BETTERSTACK_QUERY_PASSWORD", None)
            creds = get_query_credentials()
            assert creds["username"] is None
            assert creds["password"] is None

    def test_return_credentials_when_set(self) -> None:
        with patch.dict(os.environ, {
            "BETTERSTACK_QUERY_USERNAME": "test_user",
            "BETTERSTACK_QUERY_PASSWORD": "test_pass",
        }):
            creds = get_query_credentials()
            assert creds["username"] == "test_user"
            assert creds["password"] == "test_pass"

    def test_return_partial_credentials(self) -> None:
        with patch.dict(os.environ, {"BETTERSTACK_QUERY_USERNAME": "test_user"}, clear=True):
            os.environ.pop("BETTERSTACK_QUERY_PASSWORD", None)
            creds = get_query_credentials()
            assert creds["username"] == "test_user"
            assert creds["password"] is None


class TestResolveSourceAlias:
    def test_resolve_common_aliases(self) -> None:
        assert resolve_source_alias("dev") == "sweetistics-dev"
        assert resolve_source_alias("development") == "sweetistics-dev"
        assert resolve_source_alias("prod") == "sweetistics"
        assert resolve_source_alias("production") == "sweetistics"
        assert resolve_source_alias("staging") == "sweetistics-staging"
        assert resolve_source_alias("test") == "sweetistics-test"

    def test_case_insensitive_aliases(self) -> None:
        assert resolve_source_alias("DEV") == "sweetistics-dev"
        assert resolve_source_alias("Dev") == "sweetistics-dev"
        assert resolve_source_alias("PROD") == "sweetistics"
        assert resolve_source_alias("Prod") == "sweetistics"

    def test_return_original_if_not_alias(self) -> None:
        assert resolve_source_alias("custom-source") == "custom-source"
        assert resolve_source_alias("another-bucket") == "another-bucket"
        assert resolve_source_alias("sweetistics-custom") == "sweetistics-custom"

    def test_return_none_for_none_input(self) -> None:
        assert resolve_source_alias(None) is None

    def test_handle_empty_string(self) -> None:
        assert resolve_source_alias("") == ""
