"""Tests de segregación de servicios del portal (spec 013, US3 / FR-008, FR-009).

  * El grupo read (`repse.portal.routes_read`) solo registra método GET y sus
    handlers no escriben en BD.
  * Matriz de autorización: supplier → endpoints administrativos = 403;
    admin → endpoints del portal = 403 (SC-003).
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select


def _make_supplier_client(app, db_session, session_user):
    from fastapi.testclient import TestClient

    from repse.auth.passwords import hash_password  # noqa: F401  (paridad con helpers)
    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin
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
            legal_name="Proveedor ReadOnly Test",
            rfc="PRO9901014Y3",
            contact_email="ro@pro.mx",
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(supplier)
        db_session.flush()
        user = User(
            organization_id=session_user.organization_id,
            email="sup-ro@pro.mx",
            display_name="Supplier RO",
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
    c = TestClient(app)
    c.cookies.set("session", token)
    return c, supplier


def _row_counts(db_session):
    from repse.documents.models import Document
    from repse.portal.models import PortalSubmission

    docs = db_session.execute(select(func.count(Document.id))).scalar_one()
    subs = db_session.execute(select(func.count(PortalSubmission.id))).scalar_one()
    return docs, subs


def test_read_router_only_registers_get_methods():
    """Estructural: routes_read solo expone GET; routes_write nunca expone GET."""
    from repse.portal import routes_read, routes_write

    for route in routes_read.router.routes:
        assert route.methods == {"GET"}, f"{route.path} no es GET-only"
    assert len(routes_read.router.routes) == 5

    # routes_write agrupa las operaciones de escritura: upload y submit (POST)
    # más el borrado de documentos del portal (DELETE).
    for route in routes_write.router.routes:
        assert route.methods in ({"POST"}, {"DELETE"}), f"{route.path} no es de escritura"
    assert len(routes_write.router.routes) == 3


@pytest.mark.integration
def test_read_endpoints_do_not_write(app, db_session, session_user):
    client, supplier = _make_supplier_client(app, db_session, session_user)

    before = _row_counts(db_session)
    assert client.get("/api/v1/portal/compliance").status_code == 200
    assert client.get("/api/v1/portal/history/1").status_code == 200
    assert client.get("/api/v1/portal/documents?document_type_id=1").status_code == 200
    res = client.get("/api/v1/portal/submission/1")
    assert res.status_code == 200
    after = _row_counts(db_session)

    assert before == after, "una operación de consulta modificó la BD (FR-009)"


@pytest.mark.integration
def test_supplier_gets_403_on_admin_endpoints(app, db_session, session_user):
    client, _ = _make_supplier_client(app, db_session, session_user)
    for path in (
        "/api/v1/suppliers",
        "/api/v1/users",
        "/api/v1/document-types",
        "/api/v1/sectors",
        "/api/v1/supplier-types",
    ):
        res = client.get(path)
        assert res.status_code == 403, f"{path} devolvió {res.status_code} con rol supplier"


@pytest.mark.integration
def test_admin_gets_403_on_all_portal_endpoints(client_with_session):
    c = client_with_session
    assert c.get("/api/v1/portal/compliance").status_code == 403
    assert c.get("/api/v1/portal/history/1").status_code == 403
    assert c.get("/api/v1/portal/submission/1").status_code == 403
    assert c.get("/api/v1/portal/documents?document_type_id=1").status_code == 403
    assert c.get("/api/v1/portal/documents/1/download-token").status_code == 403
    assert c.post(
        "/api/v1/portal/upload",
        files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
        data={"document_type_id": "1"},
    ).status_code == 403
    assert c.post(
        "/api/v1/portal/submit/1",
        json={"coverage_period_start": None},
    ).status_code == 403
