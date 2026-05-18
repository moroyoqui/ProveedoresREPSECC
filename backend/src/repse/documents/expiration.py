"""Compute due-date by periodicity (FR-009 spec 001).

Rules:
    monthly   → end of the calendar month following the coverage period.
    bimonthly → end of the next SAT/IMSS fiscal bimester
                ({1,2}, {3,4}, {5,6}, {7,8}, {9,10}, {11,12}).
    annual    → 31-Dec of the year following the coverage period.
    none      → returns None.

Manual override is permitted at the document level (FR-010a); this function
produces the calculated default only.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from enum import StrEnum


class Periodicity(StrEnum):
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"
    ANNUAL = "annual"
    NONE = "none"


_BIMESTERS: list[tuple[int, int]] = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]


def _last_day_of_month(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _current_bimester(month: int) -> int:
    return (month - 1) // 2  # 0..5


def compute_due_date(coverage_period: date | None, periodicity: Periodicity) -> date | None:
    """Return the calculated due date, or None when not applicable."""
    if periodicity is Periodicity.NONE:
        return None
    if coverage_period is None:
        return None

    if periodicity is Periodicity.MONTHLY:
        year, month = _next_month(coverage_period.year, coverage_period.month)
        return _last_day_of_month(year, month)

    if periodicity is Periodicity.BIMONTHLY:
        idx = _current_bimester(coverage_period.month)
        next_idx = idx + 1
        if next_idx >= len(_BIMESTERS):
            return _last_day_of_month(coverage_period.year + 1, 2)
        _, last_month = _BIMESTERS[next_idx]
        return _last_day_of_month(coverage_period.year, last_month)

    if periodicity is Periodicity.ANNUAL:
        return date(coverage_period.year + 1, 12, 31)

    raise AssertionError(f"Unhandled periodicity: {periodicity}")
