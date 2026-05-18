"""Optimistic concurrency via the `If-Match` header.

Endpoints that mutate a catalog row require the client to echo the
`updated_at` they last read. If it doesn't match the row's current value the
request is rejected with `409 stale_update` — preventing silent overwrites
when two admins edit the same record (research.md §4 spec 003).

Format: ``If-Match: "<iso8601 with microseconds>"`` (RFC 7232 quotes around
the entity tag). We accept the value with or without quotes for ergonomics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Header

from repse.errors import StaleUpdate, ValidationFailure


def _parse_if_match(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationFailure(
            "Invalid If-Match header; expected ISO-8601 timestamp",
            details={"code": "invalid_if_match", "raw": raw},
        ) from exc


IfMatchHeader = Annotated[str | None, Header(alias="If-Match")]


def require_if_match(value: IfMatchHeader = None) -> datetime:
    parsed = _parse_if_match(value)
    if parsed is None:
        raise ValidationFailure(
            "If-Match header is required for this operation",
            details={"code": "if_match_required"},
        )
    return parsed


def optional_if_match(value: IfMatchHeader = None) -> datetime | None:
    return _parse_if_match(value)


def assert_fresh(expected: datetime, actual: datetime, *, current_payload: dict | None = None) -> None:
    """Raises StaleUpdate if `expected` (from header) != `actual` (from DB row).

    Comparison is done at microsecond precision; allow up to 1µs slop because
    MySQL DATETIME(6) may differ from the original in-memory value by sub-µs
    rounding when serialized via ISO string.
    """
    delta = abs((expected - actual).total_seconds())
    if delta > 1e-6:
        raise StaleUpdate(
            "Resource has been modified since you read it",
            details={
                "code": "stale_update",
                "expected_updated_at": expected.isoformat(),
                "current_updated_at": actual.isoformat(),
                **({"current": current_payload} if current_payload else {}),
            },
        )
