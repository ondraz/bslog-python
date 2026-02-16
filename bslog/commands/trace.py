"""Trace command for following a request across sources."""

from collections.abc import Callable
from typing import Any

from bslog.commands.tail import tail_logs


def trace_request(
    request_id: str,
    where: dict[str, Any] | None = None,
    executor: Callable[..., None] | None = None,
    **kwargs: Any,
) -> None:
    merged_where = {**(where or {})}
    merged_where["requestId"] = request_id

    run = executor or tail_logs
    run(where=merged_where, **kwargs)
