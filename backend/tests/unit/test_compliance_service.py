"""Unit tests for compliance.service.cell_status — the 7-state path (spec 006).

Covers the rules documented in specs/006-supplier-compliance-view/data-model.md.
"""

from __future__ import annotations

from datetime import date

import pytest

from repse.compliance.schemas import CellStatus
from repse.compliance.service import applicable_months, cell_status, effective_periodicity
from repse.document_types.models import Periodicity


def _doc(*, verified: bool = False, status: str = "valid"):
    """Tiny stand-in for a Document row — only the fields cell_status touches."""

    class _D:
        pass

    d = _D()
    d.verified = verified
    d.status = status
    return d


# ---------------------------------------------------------------------------
# cell_status — 7 estados
# ---------------------------------------------------------------------------


def test_cell_status_validated() -> None:
    doc = _doc(verified=True, status="valid")
    assert cell_status(doc, month=4, year=2026, today=date(2026, 5, 18)) == CellStatus.VALIDATED


def test_cell_status_submitted_when_unverified() -> None:
    doc = _doc(verified=False, status="valid")
    assert cell_status(doc, month=4, year=2026, today=date(2026, 5, 18)) == CellStatus.SUBMITTED


def test_cell_status_expired_overrides_verified_flag() -> None:
    """Un documento vencido tiene precedencia sobre `verified=True`."""
    doc = _doc(verified=True, status="expired")
    assert cell_status(doc, month=4, year=2026, today=date(2026, 5, 18)) == CellStatus.EXPIRED


def test_cell_status_missing_past_month_no_doc() -> None:
    assert cell_status(None, month=3, year=2026, today=date(2026, 5, 18)) == CellStatus.MISSING


def test_cell_status_pending_current_month_no_doc() -> None:
    assert cell_status(None, month=5, year=2026, today=date(2026, 5, 18)) == CellStatus.PENDING


def test_cell_status_future_no_doc() -> None:
    assert cell_status(None, month=8, year=2026, today=date(2026, 5, 18)) == CellStatus.FUTURE


def test_cell_status_validates_year_boundaries() -> None:
    """Diciembre del año anterior es missing si no hay doc; enero del siguiente es future."""
    assert cell_status(None, month=12, year=2025, today=date(2026, 5, 18)) == CellStatus.MISSING
    assert cell_status(None, month=1, year=2027, today=date(2026, 5, 18)) == CellStatus.FUTURE


# ---------------------------------------------------------------------------
# applicable_months — periodicidad
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "periodicity, expected",
    [
        (Periodicity.MONTHLY, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
        (Periodicity.BIMONTHLY, [1, 3, 5, 7, 9, 11]),
        (Periodicity.ANNUAL, [1]),
        (Periodicity.NONE, []),
    ],
)
def test_applicable_months(periodicity: Periodicity, expected: list[int]) -> None:
    assert applicable_months(periodicity) == expected


# ---------------------------------------------------------------------------
# effective_periodicity — override en requirement gana sobre el default del tipo
# ---------------------------------------------------------------------------


def test_effective_periodicity_uses_override_when_set() -> None:
    class _Req:
        periodicity_override = Periodicity.BIMONTHLY

    class _DT:
        periodicity = Periodicity.MONTHLY

    assert effective_periodicity(_Req(), _DT()) == Periodicity.BIMONTHLY


def test_effective_periodicity_falls_back_to_document_type() -> None:
    class _Req:
        periodicity_override = None

    class _DT:
        periodicity = Periodicity.ANNUAL

    assert effective_periodicity(_Req(), _DT()) == Periodicity.ANNUAL
