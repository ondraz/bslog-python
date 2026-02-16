"""Shared test fixtures for bslog tests."""

import json
from pathlib import Path

import pytest

from bslog.types import Config, Source, SourceAttributes


@pytest.fixture
def mock_source() -> Source:
    return Source(
        id="123456",
        type="source",
        attributes=SourceAttributes(
            name="test-source",
            platform="javascript",
            token="test-token-abc123",
            team_id=123456,
            table_name="test_source",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-15T00:00:00Z",
            ingesting_paused=False,
            messages_count=1000000,
            bytes_count=5368709120,
        ),
    )


@pytest.fixture
def mock_config() -> Config:
    return Config(
        defaultSource="test-source",
        defaultLimit=100,
        outputFormat="json",
        defaultLogLevel="all",
        queryHistory=[],
        savedQueries={},
    )


@pytest.fixture
def sample_log_entries() -> list[dict]:
    return [
        {
            "dt": "2024-01-15 10:30:45.123",
            "raw": json.dumps({"level": "error", "message": "Test error", "userId": "123"}),
        },
        {
            "dt": "2024-01-15 10:31:00.456",
            "raw": json.dumps({"level": "info", "message": "Test info", "subsystem": "api"}),
        },
    ]


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    config_dir = tmp_path / ".bslog"
    config_dir.mkdir()
    return config_dir
