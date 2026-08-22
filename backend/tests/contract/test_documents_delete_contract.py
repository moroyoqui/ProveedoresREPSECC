"""Spec 016: contract tests para el borrado de documentos propios en el back-office.

``DELETE /documents/{id}`` pasa de ser exclusivo de admin a admitir también al
manager **autor** de la carga. Los casos cubiertos aquí son la frontera de ese
permiso:

* 204 — el autor borra lo suyo.
* 403 — un manager intenta borrar lo de otro (``details.code=not_document_owner``).
* 403 — un viewer no alcanza la ruta (``require_role``).
* 409 — documento verificado, ventana expirada, o celda bloqueada.

El caso cross-tenant vive en ``tests/integration/test_tenant_isolation.py``.
"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select


pytestmark = pytest.mark.integration


def _minimal_pdf_bytes(unique: bytes = b"a") -> bytes:
    return (
        b"%PDF-1.4\n"
        b"%unique-" + unique + b"\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
    )


def _upload_doc(client, supplier_id: int, type_id: int, *, unique: bytes = b"del") -> int:
    files = {"file": ("d.pdf", io.BytesIO(_minimal_pdf_bytes(unique)), "application/pdf")}
    data = {"document_type_id": str(type_id), "coverage_period_start": "2026-04-01"}
    res = client.post(f"/api/v1/suppliers/{supplier_id}/documents", files=files, data=data)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _make_user(db_session, *, organization_id: int, email: str, role: str):  # type: ignore[no-untyped-def]
    """Crea un usuario adicional en la organización del session_user."""
    from repse.db.tenant_filter import with_admin_scope
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        user = User(
            organization_id=organization_id,
            email=email,
            display_name=email.split("@")[0],
            role=Role(role),
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def _client_as(app, *, user_id: int, organization_id: int, role: str):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings

    sm = SessionManager(get_settings())
    token = sm._serializer.dumps(  # type: ignore[attr-defined]
        {
            "user_id": user_id,
            "organization_id": organization_id,
            "role": role,
            "expires_at": fresh_expiry().isoformat(),
        }
    )
    c = TestClient(app)
    c.cookies.set("session", token)
    return c


def _get_doc(db_session, doc_id: int):  # type: ignore[no-untyped-def]
    from repse.db.tenant_filter import with_admin_scope
    from repse.documents.models import Document

    with with_admin_scope():
        db_session.expire_all()
        return db_session.execute(
            select(Document).where(Document.id == doc_id)
        ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# T005 — el autor borra lo suyo
# ---------------------------------------------------------------------------


def test_manager_deletes_own_document(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor1@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app,
        user_id=manager.id,
        organization_id=session_user.organization_id,
        role="manager",
    )

    doc_id = _upload_doc(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"own")

    res = mgr_client.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 204, res.text

    doc = _get_doc(db_session, doc_id)
    assert doc is not None
    assert doc.deleted_at is not None
    assert doc.is_latest is False


def test_own_document_reports_can_delete(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """El campo derivado que gobierna la visibilidad del botón (US1 lo consume)."""
    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-flag@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app, user_id=manager.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload_doc(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"flag")

    own = mgr_client.get(f"/api/v1/documents/{doc_id}").json()
    assert own["can_delete"] is True

    other = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-flag2@test.mx",
        role="manager",
    )
    other_client = _client_as(
        app, user_id=other.id, organization_id=session_user.organization_id, role="manager"
    )
    seen_by_other = other_client.get(f"/api/v1/documents/{doc_id}").json()
    assert seen_by_other["can_delete"] is False

    # El admin conserva la facultad sobre cualquier documento.
    seen_by_admin = client_with_session.get(f"/api/v1/documents/{doc_id}").json()
    assert seen_by_admin["can_delete"] is True


# ---------------------------------------------------------------------------
# T006 — no se puede borrar lo ajeno
# ---------------------------------------------------------------------------


def test_manager_cannot_delete_other_users_document(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    author = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="autor@test.mx",
        role="manager",
    )
    intruder = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="intruso@test.mx",
        role="manager",
    )
    author_client = _client_as(
        app, user_id=author.id, organization_id=session_user.organization_id, role="manager"
    )
    intruder_client = _client_as(
        app, user_id=intruder.id, organization_id=session_user.organization_id, role="manager"
    )

    doc_id = _upload_doc(author_client, seeded_supplier.id, opinion_sat_type.id, unique=b"ajn")

    res = intruder_client.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 403, res.text
    assert res.json()["error"]["details"]["code"] == "not_document_owner"

    doc = _get_doc(db_session, doc_id)
    assert doc is not None
    assert doc.deleted_at is None


def test_admin_can_delete_any_document(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """El permiso del admin no se estrecha con esta feature."""
    author = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="autor2@test.mx",
        role="manager",
    )
    author_client = _client_as(
        app, user_id=author.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload_doc(author_client, seeded_supplier.id, opinion_sat_type.id, unique=b"adm")

    res = client_with_session.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 204, res.text


# ---------------------------------------------------------------------------
# T007 — el viewer no alcanza la ruta
# ---------------------------------------------------------------------------


def test_viewer_cannot_delete(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"vwr"
    )
    viewer = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="consultor@test.mx",
        role="viewer",
    )
    viewer_client = _client_as(
        app, user_id=viewer.id, organization_id=session_user.organization_id, role="viewer"
    )

    res = viewer_client.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 403, res.text

    # Tampoco se le ofrece el control.
    body = viewer_client.get(f"/api/v1/documents/{doc_id}").json()
    assert body["can_delete"] is False


# ---------------------------------------------------------------------------
# T008 — documento verificado
# ---------------------------------------------------------------------------


def test_cannot_delete_verified_document(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-vfy@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app, user_id=manager.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload_doc(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"vfy")

    verified = mgr_client.post(f"/api/v1/documents/{doc_id}/verify", json={"note": "ok"})
    assert verified.status_code == 200, verified.text

    res = mgr_client.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 409, res.text
    assert res.json()["error"]["details"]["code"] == "document_verified"

    doc = _get_doc(db_session, doc_id)
    assert doc is not None and doc.deleted_at is None

    # Y el botón deja de ofrecerse.
    body = mgr_client.get(f"/api/v1/documents/{doc_id}").json()
    assert body["can_delete"] is False


# ---------------------------------------------------------------------------
# T009 — ventana de corrección expirada
# ---------------------------------------------------------------------------


def test_cannot_delete_after_grace_window(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    from repse.config import get_settings
    from repse.db.tenant_filter import with_admin_scope
    from repse.documents.models import Document

    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-old@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app, user_id=manager.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload_doc(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"old")

    grace = get_settings().document_delete_grace_hours
    stale = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=grace + 1)
    with with_admin_scope():
        doc = db_session.execute(select(Document).where(Document.id == doc_id)).scalar_one()
        doc.created_at = stale
        db_session.commit()

    res = mgr_client.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 409, res.text
    assert res.json()["error"]["details"]["code"] == "delete_window_expired"

    body = mgr_client.get(f"/api/v1/documents/{doc_id}").json()
    assert body["can_delete"] is False


# ---------------------------------------------------------------------------
# T010 — celda enviada a validación o ya validada
# ---------------------------------------------------------------------------


def test_cannot_delete_when_cell_is_validated(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """Spec 017: validar la celda ES verificar el documento.

    Antes de la unificación, una celda validada bloqueaba el borrado con
    ``delete_not_allowed`` a través de una tabla aparte. Ahora validar escribe en
    el documento, así que el bloqueo llega por ``document_verified``: son la
    misma condición, con un solo código.
    """
    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-cell@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app, user_id=manager.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload_doc(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"cell")

    validated = mgr_client.post(
        f"/api/v1/suppliers/{seeded_supplier.id}/compliance/validate",
        json={
            "document_type_id": opinion_sat_type.id,
            "coverage_period_start": "2026-04-01",
        },
    )
    assert validated.status_code == 200, validated.text

    res = mgr_client.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 409, res.text
    assert res.json()["error"]["details"]["code"] == "document_verified"

    doc = _get_doc(db_session, doc_id)
    assert doc is not None and doc.deleted_at is None


# ---------------------------------------------------------------------------
# T023 — el segundo DELETE responde 404 (doble clic)
# ---------------------------------------------------------------------------


def test_second_delete_returns_404(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-twice@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app, user_id=manager.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload_doc(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"twice")

    assert mgr_client.delete(f"/api/v1/documents/{doc_id}").status_code == 204
    assert mgr_client.delete(f"/api/v1/documents/{doc_id}").status_code == 404


# ---------------------------------------------------------------------------
# T026 — el archivo deja de servirse tras el borrado
# ---------------------------------------------------------------------------


def test_download_token_stops_working_after_delete(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-dl@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app, user_id=manager.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload_doc(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"dl")

    token_res = mgr_client.post(f"/api/v1/documents/{doc_id}/download-token")
    assert token_res.status_code == 200, token_res.text
    token = token_res.json()["token"]

    assert mgr_client.delete(f"/api/v1/documents/{doc_id}").status_code == 204

    served = mgr_client.get(f"/api/v1/files/{token}")
    assert served.status_code in (404, 410), served.text
