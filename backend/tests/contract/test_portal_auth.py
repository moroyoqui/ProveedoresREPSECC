"""Contract tests para el portal del proveedor — autenticación y autorización.

Principio III de la Constitución: autenticación y autorización críticas deben
tener tests antes del merge.

Casos cubiertos:
  - Sin cookie de sesión → 401
  - Rol admin/manager/viewer → 403
  - Rol supplier con supplier_id=None en sesión → 409
  - Rol supplier con supplier_id válido → 200
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def _make_supplier_client(app, *, user_id: int, organization_id: int, supplier_id: int | None):
    from fastapi.testclient import TestClient

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings

    sm = SessionManager(get_settings())
    payload_dict = {
        "user_id": user_id,
        "organization_id": organization_id,
        "role": "supplier",
        "expires_at": fresh_expiry().isoformat(),
        "supplier_id": supplier_id,
    }
    token = sm._serializer.dumps(payload_dict)  # type: ignore[attr-defined]
    c = TestClient(app)
    c.cookies.set("session", token)
    return c


def _make_role_client(app, *, user_id: int, organization_id: int, role: str):
    from fastapi.testclient import TestClient

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings

    sm = SessionManager(get_settings())
    token = sm._serializer.dumps({
        "user_id": user_id,
        "organization_id": organization_id,
        "role": role,
        "expires_at": fresh_expiry().isoformat(),
    })  # type: ignore[attr-defined]
    c = TestClient(app)
    c.cookies.set("session", token)
    return c


def test_portal_compliance_without_session_returns_401(client) -> None:
    res = client.get("/api/v1/portal/compliance")
    assert res.status_code == 401


@pytest.mark.parametrize("role", ["admin", "manager", "viewer"])
def test_portal_compliance_non_supplier_role_returns_403(
    app, session_user, role: str
) -> None:
    c = _make_role_client(
        app,
        user_id=session_user.id,
        organization_id=session_user.organization_id,
        role=role,
    )
    res = c.get("/api/v1/portal/compliance")
    assert res.status_code == 403


def test_portal_compliance_supplier_without_supplier_id_returns_409(
    app, session_user
) -> None:
    c = _make_supplier_client(
        app,
        user_id=session_user.id,
        organization_id=session_user.organization_id,
        supplier_id=None,
    )
    res = c.get("/api/v1/portal/compliance")
    assert res.status_code == 409
    body = res.json()
    assert body["error"]["code"] == "supplier_not_linked"


def test_portal_compliance_supplier_with_valid_supplier_id_returns_200(
    app, db_session, session_user, seeded_supplier
) -> None:
    from repse.db.tenant_filter import with_admin_scope
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        sup_user = User(
            organization_id=session_user.organization_id,
            email="proveedor@test.mx",
            display_name="Proveedor Test",
            role=Role.SUPPLIER,
            status=UserStatus.ACTIVE,
            supplier_id=seeded_supplier.id,
        )
        db_session.add(sup_user)
        db_session.commit()
        db_session.refresh(sup_user)

    c = _make_supplier_client(
        app,
        user_id=sup_user.id,
        organization_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
    )
    res = c.get("/api/v1/portal/compliance")
    assert res.status_code == 200
    body = res.json()
    assert "supplier" in body
    assert "monthly_requirements" in body
    assert "one_time_requirements" in body
