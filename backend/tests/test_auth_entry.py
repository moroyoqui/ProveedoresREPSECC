"""Tests del gating por audiencia en POST /auth/login (spec 013, US4 / FR-013).

Reglas:
  * audience omitido → "backoffice" (retrocompatible).
  * audience="portal" exige rol supplier; audience="backoffice" lo excluye.
  * El mismatch responde EXACTAMENTE igual que credenciales inválidas, para no
    revelar la validez de la credencial.
"""
from __future__ import annotations

import pytest

PASSWORD = "s3cret-Entry-013"


@pytest.fixture()
def login_users(db_session, session_user):
    """Crea un usuario supplier (con empresa) y devuelve (admin_email, supplier_email).

    El admin de `session_user` no tiene contraseña; se le asigna una aquí.
    """
    from sqlalchemy import select

    from repse.auth.passwords import hash_password
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        set_current_tenant(session_user.organization_id)
        admin = db_session.get(User, session_user.id)
        admin.password_hash = hash_password(PASSWORD)

        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == session_user.organization_id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        supplier = Supplier(
            organization_id=session_user.organization_id,
            supplier_type_id=st.id,
            legal_name="Proveedor Entry Test",
            rfc="PET9901013Y3",
            contact_email="entry@pet.mx",
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(supplier)
        db_session.flush()
        sup_user = User(
            organization_id=session_user.organization_id,
            email="sup-entry@pet.mx",
            display_name="Supplier Entry",
            role=Role.SUPPLIER,
            status=UserStatus.ACTIVE,
            supplier_id=supplier.id,
            password_hash=hash_password(PASSWORD),
        )
        db_session.add(sup_user)
        db_session.commit()
    return session_user.email, sup_user.email


def _login(client, email, password=PASSWORD, audience=None):
    body = {"email": email, "password": password}
    if audience is not None:
        body["audience"] = audience
    return client.post("/api/v1/auth/login", json=body)


def _invalid_credentials_body(client, email):
    """Respuesta de referencia: contraseña incorrecta para el mismo email."""
    res = _login(client, email, password="definitely-wrong-password")
    assert res.status_code == 400
    return res.json()


@pytest.mark.integration
def test_login_without_audience_works_for_backoffice_roles(client, login_users):
    admin_email, _ = login_users
    res = _login(client, admin_email)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "session=" in res.headers.get("set-cookie", "")


@pytest.mark.integration
def test_portal_audience_with_supplier_role_succeeds(client, login_users):
    _, supplier_email = login_users
    res = _login(client, supplier_email, audience="portal")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "session=" in res.headers.get("set-cookie", "")


@pytest.mark.integration
def test_portal_audience_with_admin_role_is_indistinguishable_from_bad_password(client, login_users):
    admin_email, _ = login_users
    res = _login(client, admin_email, audience="portal")
    assert res.status_code == 400
    # Byte-a-byte equivalente (código y estructura) al caso de contraseña mala.
    assert res.json() == _invalid_credentials_body(client, admin_email)
    assert res.json()["error"]["details"]["code"] == "invalid_credentials"


@pytest.mark.integration
@pytest.mark.parametrize("audience", [None, "backoffice"])
def test_backoffice_audience_with_supplier_role_is_indistinguishable_from_bad_password(
    client, login_users, audience
):
    _, supplier_email = login_users
    res = _login(client, supplier_email, audience=audience)
    assert res.status_code == 400
    assert res.json() == _invalid_credentials_body(client, supplier_email)
    assert res.json()["error"]["details"]["code"] == "invalid_credentials"


@pytest.mark.integration
def test_invalid_audience_value_is_rejected(client, login_users):
    admin_email, _ = login_users
    res = _login(client, admin_email, audience="otra-cosa")
    assert res.status_code in (400, 422)
    # Error de validación de payload, no de credenciales.
    assert "invalid_credentials" not in res.text
