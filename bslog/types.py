"""Type definitions for bslog."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceAttributes:
    name: str
    platform: str
    token: str
    team_id: int
    table_name: str
    created_at: str
    updated_at: str
    ingesting_paused: bool
    messages_count: int
    bytes_count: int


@dataclass
class Source:
    id: str
    type: str
    attributes: SourceAttributes


@dataclass
class LogEntry:
    dt: str
    raw: str
    extra: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        if key == "dt":
            return self.dt
        if key == "raw":
            return self.raw
        return self.extra.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "dt":
            self.dt = value
        elif key == "raw":
            self.raw = value
        else:
            self.extra[key] = value

    def __contains__(self, key: str) -> bool:
        if key in ("dt", "raw"):
            return True
        return key in self.extra

    def get(self, key: str, default: Any = None) -> Any:
        if key == "dt":
            return self.dt
        if key == "raw":
            return self.raw
        return self.extra.get(key, default)

    def keys(self) -> list[str]:
        return ["dt", "raw", *self.extra.keys()]

    def items(self) -> list[tuple[str, Any]]:
        return [("dt", self.dt), ("raw", self.raw), *self.extra.items()]

    def to_dict(self) -> dict[str, Any]:
        return {"dt": self.dt, "raw": self.raw, **self.extra}


@dataclass
class QueryOptions:
    limit: int | None = None
    level: str | None = None
    subsystem: str | None = None
    since: str | None = None
    until: str | None = None
    search: str | None = None
    where: dict[str, Any] | None = None
    fields: list[str] | None = None
    source: str | None = None
    sources: list[str] | None = None
    verbose: bool | None = None


@dataclass
class Config:
    defaultSource: str | None = None  # noqa: N815
    defaultLimit: int | None = 100  # noqa: N815
    outputFormat: str | None = "json"  # noqa: N815
    defaultLogLevel: str | None = "all"  # noqa: N815
    queryBaseUrl: str | None = None  # noqa: N815
    queryHistory: list[str] = field(default_factory=list)  # noqa: N815
    savedQueries: dict[str, str] = field(default_factory=dict)  # noqa: N815


@dataclass
class Pagination:
    first: str | None = None
    last: str | None = None
    prev: str | None = None
    next: str | None = None


@dataclass
class ApiResponse[T]:
    data: T
    pagination: Pagination | None = None
