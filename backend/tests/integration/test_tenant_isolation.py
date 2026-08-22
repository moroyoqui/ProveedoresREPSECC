"""Multi-tenant isolation negative test (T038 spec 001).

Asserts that a user authenticated in Org B cannot reach resources of Org A —
the server responds 404, not 403 (so tenant existence is not leaked).
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def test_org_a_supplier_not_visible_from_org_b(
    client_with_session_org_a,
    client_with_session_org_b,
    supplier_in_org_a,
) -> None:
    # Org A sees its own supplier.
    res_a = client_with_session_org_a.get(f"/api/v1/suppliers/{supplier_in_org_a.id}")
    assert res_a.status_code == 200

    # Org B gets 404, NOT 403 (constraint of the contracts/ README).
    res_b = client_with_session_org_b.get(f"/api/v1/suppliers/{supplier_in_org_a.id}")
    assert res_b.status_code == 404
    assert res_b.json()["error"]["code"] == "not_found"


def test_org_a_document_not_visible_from_org_b(
    client_with_session_org_a,
    client_with_session_org_b,
    document_in_org_a,
) -> None:
    res_a = client_with_session_org_a.get(f"/api/v1/documents/{document_in_org_a.id}")
    assert res_a.status_code == 200

    res_b = client_with_session_org_b.get(f"/api/v1/documents/{document_in_org_a.id}")
    assert res_b.status_code == 404


def test_org_a_document_not_deletable_from_org_b(
    client_with_session_org_a,
    client_with_session_org_b,
    document_in_org_a,
) -> None:
    """Spec 016: abrir el borrado más allá del admin no abre una vía cross-tenant.

    Org B es admin en su propia organización, así que el rechazo no puede venir
    de `require_role`: tiene que venir del filtro de tenant, y como 404 para no
    revelar que el documento existe.
    """
    res_b = client_with_session_org_b.delete(f"/api/v1/documents/{document_in_org_a.id}")
    assert res_b.status_code == 404
    assert res_b.json()["error"]["code"] == "not_found"

    # La fila de A sigue intacta y su dueño la sigue viendo.
    res_a = client_with_session_org_a.get(f"/api/v1/documents/{document_in_org_a.id}")
    assert res_a.status_code == 200


def test_org_a_cell_not_validatable_from_org_b(
    client_with_session_org_a,
    client_with_session_org_b,
    document_in_org_a,
) -> None:
    """Spec 017: unificar la validación no abre una vía cross-tenant.

    Org B es admin en su organización, así que el rechazo no puede venir del
    rol: viene de que el proveedor de A no existe para B, y como 404.
    """
    body = {
        "document_type_id": document_in_org_a.document_type_id,
        "coverage_period_start": (
            document_in_org_a.coverage_period_start.isoformat()
            if document_in_org_a.coverage_period_start
            else None
        ),
    }
    res = client_with_session_org_b.post(
        f"/api/v1/suppliers/{document_in_org_a.supplier_id}/compliance/validate", json=body
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"

    # El documento de A sigue sin verificar.
    doc = client_with_session_org_a.get(f"/api/v1/documents/{document_in_org_a.id}").json()
    assert doc["verified"] is False
