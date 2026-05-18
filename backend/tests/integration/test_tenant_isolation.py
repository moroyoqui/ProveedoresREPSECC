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
