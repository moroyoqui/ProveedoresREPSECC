"""Unit tests for due-date calculator (no DB needed)."""

from datetime import date

import pytest

from repse.documents.expiration import Periodicity, compute_due_date


@pytest.mark.parametrize(
    "coverage, expected",
    [
        (date(2026, 4, 1), date(2026, 5, 31)),    # April → end of May
        (date(2026, 12, 1), date(2027, 1, 31)),   # December → end of next January
        (date(2026, 2, 1), date(2026, 3, 31)),    # February → end of March
    ],
)
def test_monthly(coverage: date, expected: date) -> None:
    assert compute_due_date(coverage, Periodicity.MONTHLY) == expected


@pytest.mark.parametrize(
    "coverage, expected",
    [
        (date(2026, 1, 15), date(2026, 4, 30)),   # ene-feb → mar-abr ends Apr 30
        (date(2026, 7, 31), date(2026, 10, 31)),  # jul-ago → sep-oct ends Oct 31
        (date(2026, 11, 1), date(2027, 2, 28)),   # nov-dic → ene-feb 2027 ends Feb 28
    ],
)
def test_bimonthly(coverage: date, expected: date) -> None:
    assert compute_due_date(coverage, Periodicity.BIMONTHLY) == expected


def test_annual() -> None:
    assert compute_due_date(date(2026, 3, 1), Periodicity.ANNUAL) == date(2027, 12, 31)


def test_none_periodicity_returns_none() -> None:
    assert compute_due_date(date(2026, 1, 1), Periodicity.NONE) is None


def test_none_coverage_returns_none() -> None:
    assert compute_due_date(None, Periodicity.MONTHLY) is None
