"""Unit tests for the dashboard aggregation helpers (spec 005).

Pure functions — no DB. Cover SC-007 (pie sums to 100), the cell→state
mapping, reference-date semantics (FR-011/FR-012) and filter validation.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from repse.compliance.schemas import CellStatus
from repse.dashboard.service import (
    _cell_to_dashboard_state,
    _hamilton_percentages,
    normalize_filters,
    resolve_reference_date,
)
from repse.documents.models import DocumentStatus
from repse.errors import ValidationFailure


@pytest.mark.parametrize(
    "counts",
    [
        {"valid": 412, "expiring_soon": 54, "expired": 79, "missing": 61},
        {"valid": 1, "expiring_soon": 1, "expired": 1, "missing": 0},
        {"valid": 0, "expiring_soon": 0, "expired": 0, "missing": 0},
        {"valid": 7, "expiring_soon": 7, "expired": 7, "missing": 7},
    ],
)
def test_hamilton_sums_to_100_or_0(counts) -> None:
    pct = _hamilton_percentages(counts)
    total = sum(pct.values())
    assert total in (0, 100)
    if sum(counts.values()) > 0:
        assert total == 100


def test_cell_mapping_expired_and_missing() -> None:
    assert _cell_to_dashboard_state(CellStatus.EXPIRED, 1, {}) == "expired"
    assert _cell_to_dashboard_state(CellStatus.MISSING, None, {}) == "missing"


def test_cell_mapping_present_splits_valid_vs_expiring() -> None:
    states = {10: DocumentStatus.VALID, 11: DocumentStatus.EXPIRING_SOON}
    assert _cell_to_dashboard_state(CellStatus.SUBMITTED, 10, states) == "valid"
    assert _cell_to_dashboard_state(CellStatus.SUBMITTED, 11, states) == "expiring_soon"
    assert _cell_to_dashboard_state(CellStatus.VALIDATED, 10, states) == "valid"


def test_cell_mapping_excludes_pending_future_not_required() -> None:
    for cs in (CellStatus.PENDING, CellStatus.FUTURE, CellStatus.NOT_REQUIRED):
        assert _cell_to_dashboard_state(cs, None, {}) is None


def test_reference_date_current_vs_past_year() -> None:
    tz = "America/Mexico_City"
    now = datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo(tz))
    assert resolve_reference_date(year=2026, tz_name=tz, now=now) == date(2026, 6, 15)
    assert resolve_reference_date(year=2024, tz_name=tz, now=now) == date(2024, 12, 31)


def test_normalize_filters_rejects_bad_year_and_status() -> None:
    with pytest.raises(ValidationFailure) as ei:
        normalize_filters(
            year=2019, supplier_type=None, document_type=None, supplier=None,
            status=None, include_inactive=False, current_year=2026,
        )
    assert ei.value.details["code"] == "invalid_year"

    with pytest.raises(ValidationFailure) as ei2:
        normalize_filters(
            year=2026, supplier_type=None, document_type=None, supplier=None,
            status=["nope"], include_inactive=False, current_year=2026,
        )
    assert ei2.value.details["code"] == "invalid_status"


def test_normalize_filters_dedupes_and_sorts() -> None:
    f = normalize_filters(
        year=None, supplier_type=[3, 1, 3], document_type=[], supplier=[9, 9],
        status=["expired", "valid", "valid"], include_inactive=True, current_year=2026,
    )
    assert f.year == 2026
    assert f.supplier_type_ids == [1, 3]
    assert f.supplier_ids == [9]
    assert f.statuses == ["expired", "valid"]
    assert f.include_inactive is True
