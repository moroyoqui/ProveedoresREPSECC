"""Contract tests for GET /api/v1/dashboard/compliance (spec 005)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_default_view_shape_and_pie_sums_100(
    client_with_session, db_session, session_user, seeded_supplier
) -> None:
    res = client_with_session.get("/api/v1/dashboard/compliance")
    assert res.status_code == 200, res.text
    body = res.json()

    # Shape per contract.
    for key in (
        "filters", "pie", "by_document_type", "kpis", "suppliers",
        "available_years", "calculated_at", "empty_reason",
    ):
        assert key in body
    assert set(body["kpis"].keys()) == {
        "global_compliance_percent", "active_suppliers",
        "at_risk_suppliers", "expiring_30d",
    }

    # SC-007: the four slices sum to exactly 100 whenever there is data.
    if body["pie"]:
        assert sum(s["percent"] for s in body["pie"]) == 100


def test_invalid_year_returns_400(client_with_session) -> None:
    res = client_with_session.get("/api/v1/dashboard/compliance?year=1999")
    assert res.status_code == 400
    assert res.json()["error"]["details"]["code"] == "invalid_year"


def test_invalid_status_returns_400(client_with_session) -> None:
    res = client_with_session.get("/api/v1/dashboard/compliance?status=banana")
    assert res.status_code == 400
    assert res.json()["error"]["details"]["code"] == "invalid_status"


def test_future_year_rejected(client_with_session) -> None:
    from datetime import date

    res = client_with_session.get(
        f"/api/v1/dashboard/compliance?year={date.today().year + 1}"
    )
    assert res.status_code == 400
    assert res.json()["error"]["details"]["code"] == "invalid_year"


def test_available_years_includes_current_year(
    client_with_session, seeded_supplier
) -> None:
    from datetime import date

    res = client_with_session.get("/api/v1/dashboard/compliance")
    assert res.status_code == 200
    years = res.json()["available_years"]
    assert date.today().year in years
    assert all(isinstance(y, int) for y in years)


def test_repeatable_params_and_foreign_ids(
    client_with_session, seeded_supplier
) -> None:
    # Params repetibles + estado válido → 200.
    res = client_with_session.get(
        "/api/v1/dashboard/compliance"
        "?supplier_type=1&supplier_type=2&status=valid&status=missing"
        "&include_inactive=true"
    )
    assert res.status_code == 200, res.text

    # IDs que no pertenecen al tenant se ignoran (no error), no exponen nada.
    res2 = client_with_session.get(
        "/api/v1/dashboard/compliance?document_type=99999999"
    )
    assert res2.status_code == 200, res2.text


def test_requires_session(app) -> None:
    from fastapi.testclient import TestClient

    res = TestClient(app).get("/api/v1/dashboard/compliance")
    assert res.status_code == 401
