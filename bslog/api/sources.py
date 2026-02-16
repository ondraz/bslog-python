"""Sources API for Better Stack."""

from __future__ import annotations

from typing import Any

from bslog.api.client import BetterStackClient
from bslog.types import Source, SourceAttributes


class SourcesAPI:
    def __init__(self) -> None:
        self.client = BetterStackClient()

    def list_page(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        params = f"?page={page}&per_page={per_page}"
        return self.client.telemetry(f"/sources{params}")  # type: ignore[no-any-return]

    def list_all(self) -> list[Source]:
        sources: list[Source] = []
        page = 1
        has_more = True

        while has_more:
            response = self.list_page(page, 50)
            for item in response.get("data", []):
                sources.append(_parse_source(item))
            pagination = response.get("pagination", {})
            has_more = pagination.get("next") is not None
            page += 1

        return sources

    def get(self, source_id: str) -> Source:
        response: dict[str, Any] = self.client.telemetry(f"/sources/{source_id}")  # type: ignore[assignment]
        return _parse_source(response["data"])

    def find_by_name(self, name: str) -> Source | None:
        sources = self.list_all()
        for source in sources:
            if source.attributes.name == name:
                return source
        return None


def _parse_source(data: dict[str, Any]) -> Source:
    attrs = data.get("attributes", {})
    return Source(
        id=str(data.get("id", "")),
        type=str(data.get("type", "")),
        attributes=SourceAttributes(
            name=attrs.get("name", ""),
            platform=attrs.get("platform", ""),
            token=attrs.get("token", ""),
            team_id=attrs.get("team_id", 0),
            table_name=attrs.get("table_name", ""),
            created_at=attrs.get("created_at", ""),
            updated_at=attrs.get("updated_at", ""),
            ingesting_paused=attrs.get("ingesting_paused", False),
            messages_count=attrs.get("messages_count", 0),
            bytes_count=attrs.get("bytes_count", 0),
        ),
    )
