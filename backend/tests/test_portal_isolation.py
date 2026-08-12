"""Tenant-isolation tests for portal endpoints (US1 — T006).

Verifies that supplier data is strictly isolated:
1. Two suppliers in the same org each see only their own compliance grid.
2. A forged session that points to a supplier in org Y while authenticated as
   org X receives 404 — the service's cross-org check prevents data leakage.
"""
from __future__ import annotations

import pytest


_COMPLIANCE_URL = "/api/v1/portal/compliance"


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_supplier_client(app, db_session, *, organization_id, rfc, email):
    """Create a supplier + supplier-role user in org; return (TestClient, supplier)."""
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        set_current_tenant(organization_id)
        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == organization_id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        supplier = Supplier(
            organization_id=organization_id,
            supplier_type_id=st.id,
            legal_name=f"Proveedor {rfc}",
            rfc=rfc,
            contact_email=email,
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(supplier)
        db_session.flush()
        user = User(
            organization_id=organization_id,
            email=email,
            display_name=f"Supplier {rfc}",
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
            "organization_id": organization_id,
            "role": "supplier",
            "supplier_id": supplier.id,
            "expires_at": fresh_expiry().isoformat(),
        }
    )
    c = TestClient(app)
    c.cookies.set("session", token)
    return c, supplier


def _make_org(db_session, *, rfc, email):
    """Create a fresh organization with a provisioned supplier type."""
    from repse.db.tenant_filter import with_admin_scope
    from repse.organizations.models import Organization
    from repse.supplier_types.provisioning import provision_organization

    with with_admin_scope():
        org = Organization(legal_name=f"Org {rfc}", rfc=rfc, contact_email=email)
        db_session.add(org)
        db_session.flush()
        provision_organization(db_session, organization_id=org.id)
        db_session.commit()
    return org


# ─── Test 1: two suppliers in the same org ───────────────────────────────────


@pytest.mark.integration
def test_supplier_sees_only_own_data_same_org(app, db_session, session_user):
    """Supplier A and Supplier B in the same org each receive only their own grid."""
    client_a, supplier_a = _make_supplier_client(
        app,
        db_session,
        organization_id=session_user.organization_id,
        rfc="ISA9901010Y3",
        email="iso-a@test.mx",
    )
    client_b, supplier_b = _make_supplier_client(
        app,
        db_session,
        organization_id=session_user.organization_id,
        rfc="ISB9901010Y3",
        email="iso-b@test.mx",
    )

    resp_a = client_a.get(_COMPLIANCE_URL)
    resp_b = client_b.get(_COMPLIANCE_URL)

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    id_in_a = resp_a.json()["supplier"]["id"]
    id_in_b = resp_b.json()["supplier"]["id"]

    assert id_in_a == supplier_a.id
    assert id_in_b == supplier_b.id
    # Each user sees a different supplier — not the other one
    assert id_in_a != supplier_b.id
    assert id_in_b != supplier_a.id


# ─── Test 2: cross-org access is blocked ─────────────────────────────────────


@pytest.mark.integration
def test_supplier_cannot_access_different_org_data(app, db_session):
    """Forged session: org-X credentials pointing to supplier in org Y → 404.

    The service checks supplier.organization_id against the session's
    organization_id and raises NotFound if they differ.
    """
    from fastapi.testclient import TestClient

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings

    org_x = _make_org(db_session, rfc="OX9901010Y3", email="x@org.mx")
    org_y = _make_org(db_session, rfc="OY9901010Y3", email="y@org.mx")

    _, supplier_x = _make_supplier_client(
        app, db_session,
        organization_id=org_x.id,
        rfc="ISX9901010Y3",
        email="iso-x@test.mx",
    )
    _, supplier_y = _make_supplier_client(
        app, db_session,
        organization_id=org_y.id,
        rfc="ISY9901010Y3",
        email="iso-y@test.mx",
    )

    # Craft a forged session: authenticated as org_x but pointing to supplier_y
    sm = SessionManager(get_settings())
    forged_token = sm._serializer.dumps(  # type: ignore[attr-defined]
        {
            "user_id": 99999,
            "organization_id": org_x.id,
            "role": "supplier",
            "supplier_id": supplier_y.id,  # belongs to org_y — cross-org
            "expires_at": fresh_expiry().isoformat(),
        }
    )
    forged_client = TestClient(app)
    forged_client.cookies.set("session", forged_token)

    resp = forged_client.get(_COMPLIANCE_URL)
    # The service finds supplier_y but its org != org_x → NotFound → 404
    assert resp.status_code == 404
