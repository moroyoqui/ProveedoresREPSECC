"""Integration tests for GET /api/v1/suppliers/{id}/compliance (spec 006).

Covers:
  * happy path: estructura de respuesta correcta con monthly_requirements y
    one_time_requirements.
  * negativo multi-tenant: usuario de Org B no puede ver compliance de proveedor
    de Org A (404, no 403).
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def test_compliance_returns_grid_structure(
    client_with_session, seeded_supplier
) -> None:
    res = client_with_session.get(
        f"/api/v1/suppliers/{seeded_supplier.id}/compliance?year=2026"
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["year"] == 2026

    supplier = body["supplier"]
    assert supplier["id"] == seeded_supplier.id
    assert supplier["legal_name"] == seeded_supplier.legal_name
    assert supplier["rfc"] == seeded_supplier.rfc
    assert "supplier_type" in supplier
    assert "compliance_percent" in supplier

    assert isinstance(body["monthly_requirements"], list)
    assert isinstance(body["one_time_requirements"], list)

    # Cada monthly_requirement debe tener exactamente 12 celdas.
    for req in body["monthly_requirements"]:
        assert len(req["cells"]) == 12
        months = [c["month"] for c in req["cells"]]
        assert months == list(range(1, 13))
        for cell in req["cells"]:
            assert cell["status"] in {
                "validated",
                "submitted",
                "expired",
                "missing",
                "pending",
                "future",
                "not_required",
            }


def test_compliance_defaults_to_current_year_when_omitted(
    client_with_session, seeded_supplier
) -> None:
    from datetime import date

    res = client_with_session.get(
        f"/api/v1/suppliers/{seeded_supplier.id}/compliance"
    )
    assert res.status_code == 200
    assert res.json()["year"] == date.today().year


def test_compliance_rejects_year_out_of_range(
    client_with_session, seeded_supplier
) -> None:
    res = client_with_session.get(
        f"/api/v1/suppliers/{seeded_supplier.id}/compliance?year=1999"
    )
    assert res.status_code == 400


def test_compliance_multi_tenant_isolation_returns_404(
    client_with_session_org_a,
    client_with_session_org_b,
    supplier_in_org_a,
) -> None:
    # Org A puede consultar su propio proveedor.
    res_a = client_with_session_org_a.get(
        f"/api/v1/suppliers/{supplier_in_org_a.id}/compliance?year=2026"
    )
    assert res_a.status_code == 200

    # Org B no debe poder verlo — 404, no 403 (no leak de existencia).
    res_b = client_with_session_org_b.get(
        f"/api/v1/suppliers/{supplier_in_org_a.id}/compliance?year=2026"
    )
    assert res_b.status_code == 404
    assert res_b.json()["error"]["code"] == "not_found"
