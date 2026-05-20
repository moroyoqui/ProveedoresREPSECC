"""Tests de aislamiento multi-tenant para el portal del proveedor.

Principio II de la Constitución: todos los queries deben estar acotados por
tenant; los casos negativos de aislamiento son obligatorios.

Casos cubiertos:
  - Supplier A no puede ver datos del supplier B (misma organización)
  - Supplier de la organización X no puede ver datos de la organización Y
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def _make_supplier_client(app, *, user_id: int, organization_id: int, supplier_id: int):
    from fastapi.testclient import TestClient

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings

    sm = SessionManager(get_settings())
    token = sm._serializer.dumps({
        "user_id": user_id,
        "organization_id": organization_id,
        "role": "supplier",
        "expires_at": fresh_expiry().isoformat(),
        "supplier_id": supplier_id,
    })  # type: ignore[attr-defined]
    c = TestClient(app)
    c.cookies.set("session", token)
    return c


def _make_org_with_supplier(db_session, *, suffix: str):
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.organizations.models import Organization
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
    from repse.supplier_types.provisioning import provision_organization
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.users.models import Role, User, UserStatus
    from sqlalchemy import select

    with with_admin_scope():
        org = Organization(
            legal_name=f"Org {suffix}",
            rfc=f"ORG{suffix}01AAA"[:13],
            contact_email=f"admin-{suffix}@iso.mx",
        )
        db_session.add(org)
        db_session.flush()
        provision_organization(db_session, organization_id=org.id)
        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == org.id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        set_current_tenant(org.id)
        supplier = Supplier(
            organization_id=org.id,
            supplier_type_id=st.id,
            legal_name=f"Proveedor {suffix}",
            rfc=f"PRV{suffix}01AAA"[:13],
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(supplier)
        db_session.flush()
        sup_user = User(
            organization_id=org.id,
            email=f"proveedor-{suffix}@iso.mx",
            display_name=f"Proveedor {suffix}",
            role=Role.SUPPLIER,
            status=UserStatus.ACTIVE,
            supplier_id=supplier.id,
        )
        db_session.add(sup_user)
        db_session.commit()
        db_session.refresh(sup_user)
        db_session.refresh(supplier)

    return org, supplier, sup_user


def test_supplier_a_sees_own_data_not_supplier_b(app, db_session) -> None:
    """Dos suppliers en la misma organización no deben ver datos del otro."""
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.organizations.models import Organization
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
    from repse.supplier_types.provisioning import provision_organization
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.users.models import Role, User, UserStatus
    from sqlalchemy import select

    with with_admin_scope():
        org = Organization(
            legal_name="Org Shared",
            rfc="SHRD900101AAA"[:13],
            contact_email="admin-shared@iso.mx",
        )
        db_session.add(org)
        db_session.flush()
        provision_organization(db_session, organization_id=org.id)
        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == org.id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        set_current_tenant(org.id)

        supplier_a = Supplier(
            organization_id=org.id,
            supplier_type_id=st.id,
            legal_name="Supplier Alpha",
            rfc="SALPHA01AAA"[:13],
            status=SupplierStatus.ACTIVE,
        )
        supplier_b = Supplier(
            organization_id=org.id,
            supplier_type_id=st.id,
            legal_name="Supplier Beta",
            rfc="SBETA001AAA"[:13],
            status=SupplierStatus.ACTIVE,
        )
        db_session.add_all([supplier_a, supplier_b])
        db_session.flush()

        user_a = User(
            organization_id=org.id,
            email="proveedor-a@iso.mx",
            display_name="User A",
            role=Role.SUPPLIER,
            status=UserStatus.ACTIVE,
            supplier_id=supplier_a.id,
        )
        user_b = User(
            organization_id=org.id,
            email="proveedor-b@iso.mx",
            display_name="User B",
            role=Role.SUPPLIER,
            status=UserStatus.ACTIVE,
            supplier_id=supplier_b.id,
        )
        db_session.add_all([user_a, user_b])
        db_session.commit()
        db_session.refresh(user_a)
        db_session.refresh(user_b)
        db_session.refresh(supplier_a)
        db_session.refresh(supplier_b)

    client_a = _make_supplier_client(
        app,
        user_id=user_a.id,
        organization_id=org.id,
        supplier_id=supplier_a.id,
    )
    client_b = _make_supplier_client(
        app,
        user_id=user_b.id,
        organization_id=org.id,
        supplier_id=supplier_b.id,
    )

    res_a = client_a.get("/api/v1/portal/compliance")
    res_b = client_b.get("/api/v1/portal/compliance")

    assert res_a.status_code == 200
    assert res_b.status_code == 200

    body_a = res_a.json()
    body_b = res_b.json()

    # Cada proveedor ve su propia empresa, no la del otro.
    assert body_a["supplier"]["id"] == supplier_a.id
    assert body_b["supplier"]["id"] == supplier_b.id
    assert body_a["supplier"]["id"] != body_b["supplier"]["id"]


def test_supplier_cross_org_isolation(app, db_session) -> None:
    """Un supplier de la org X no puede ver datos de la org Y."""
    org_x, supplier_x, user_x = _make_org_with_supplier(db_session, suffix="XI")
    org_y, supplier_y, user_y = _make_org_with_supplier(db_session, suffix="YI")

    client_x = _make_supplier_client(
        app,
        user_id=user_x.id,
        organization_id=org_x.id,
        supplier_id=supplier_x.id,
    )
    client_y = _make_supplier_client(
        app,
        user_id=user_y.id,
        organization_id=org_y.id,
        supplier_id=supplier_y.id,
    )

    res_x = client_x.get("/api/v1/portal/compliance")
    res_y = client_y.get("/api/v1/portal/compliance")

    assert res_x.status_code == 200
    assert res_y.status_code == 200

    body_x = res_x.json()
    body_y = res_y.json()

    assert body_x["supplier"]["id"] == supplier_x.id
    assert body_y["supplier"]["id"] == supplier_y.id
    # La organización que cada uno ve es la suya propia.
    assert body_x["supplier"]["id"] != body_y["supplier"]["id"]
