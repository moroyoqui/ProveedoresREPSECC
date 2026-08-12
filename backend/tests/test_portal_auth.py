"""Auth tests for GET /api/v1/portal/compliance (US1 — T005).

Covers the four auth gates on portal endpoints:
- No session cookie                          → 401
- Roles admin / manager / viewer             → 403
- Supplier role without supplier_id          → 409 supplier_not_linked
- Supplier role with valid supplier_id       → 200
"""
from __future__ import annotations

import pytest


_COMPLIANCE_URL = "/api/v1/portal/compliance"


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _token(sm, *, user_id, organization_id, role, supplier_id=None):
    from repse.auth.session import fresh_expiry

    payload: dict = {
        "user_id": user_id,
        "organization_id": organization_id,
        "role": role,
        "expires_at": fresh_expiry().isoformat(),
    }
    if supplier_id is not None:
        payload["supplier_id"] = supplier_id
    return sm._serializer.dumps(payload)  # type: ignore[attr-defined]


def _client_with_token(app, token):
    from fastapi.testclient import TestClient

    c = TestClient(app)
    c.cookies.set("session", token)
    return c


def _make_session_manager():
    from repse.auth.session import SessionManager
    from repse.config import get_settings

    return SessionManager(get_settings())


# ─── 401 — no cookie ─────────────────────────────────────────────────────────


@pytest.mark.integration
def test_compliance_no_cookie_returns_401(client):
    """No session cookie → 401 Unauthenticated."""
    resp = client.get(_COMPLIANCE_URL)
    assert resp.status_code == 401


# ─── 403 — wrong role ────────────────────────────────────────────────────────


@pytest.mark.parametrize("role", ["admin", "manager", "viewer"])
@pytest.mark.integration
def test_compliance_non_supplier_role_returns_403(app, session_user, role):
    """Roles admin/manager/viewer are rejected with 403 on portal endpoints."""
    sm = _make_session_manager()
    token = _token(sm, user_id=session_user.id, organization_id=session_user.organization_id, role=role)
    resp = _client_with_token(app, token).get(_COMPLIANCE_URL)
    assert resp.status_code == 403


# ─── 409 — supplier role but no supplier_id in session ───────────────────────


@pytest.mark.integration
def test_compliance_supplier_without_supplier_id_returns_409(app, session_user):
    """supplier role + supplier_id absent from session → 409 supplier_not_linked.

    supplier_id is omitted from the token dict so session.read() returns None.
    """
    sm = _make_session_manager()
    token = _token(sm, user_id=session_user.id, organization_id=session_user.organization_id, role="supplier")
    resp = _client_with_token(app, token).get(_COMPLIANCE_URL)
    assert resp.status_code == 409
    assert resp.json()["error"]["details"]["code"] == "supplier_not_linked"


# ─── 200 — supplier with valid supplier_id ───────────────────────────────────


@pytest.mark.integration
def test_compliance_supplier_with_valid_supplier_id_returns_200(app, db_session, session_user):
    """Supplier role + supplier_id in session → 200 ComplianceGridOut."""
    from sqlalchemy import select

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == session_user.organization_id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        supplier = Supplier(
            organization_id=session_user.organization_id,
            supplier_type_id=st.id,
            legal_name="Proveedor Auth Test",
            rfc="PAT9901010Y3",
            contact_email="auth@pat.mx",
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(supplier)
        db_session.flush()
        user = User(
            organization_id=session_user.organization_id,
            email="sup-auth@pat.mx",
            display_name="Supplier Auth",
            role=Role.SUPPLIER,
            status=UserStatus.ACTIVE,
            supplier_id=supplier.id,
        )
        db_session.add(user)
        db_session.flush()
        db_session.commit()

    sm = SessionManager(get_settings())
    token = sm._serializer.dumps(  # type: ignore[attr-defined]
        {
            "user_id": user.id,
            "organization_id": session_user.organization_id,
            "role": "supplier",
            "supplier_id": supplier.id,
            "expires_at": fresh_expiry().isoformat(),
        }
    )
    resp = _client_with_token(app, token).get(_COMPLIANCE_URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["supplier"]["id"] == supplier.id
    assert "monthly_requirements" in body
    assert "one_time_requirements" in body
