"""Spec 017: "validado" (celda) y "verificado" (documento) son el mismo hecho.

Antes de esta feature convivían dos marcas que podían contradecirse: la rejilla
leía `compliance_cell_validations` y la pantalla de documentos leía
`documents.verified`. Aquí se fija que el documento es la única fuente de verdad
y que la celda deriva su estado de él, se escriba desde donde se escriba.
"""

from __future__ import annotations

import io

import pytest


pytestmark = pytest.mark.integration


def _pdf(unique: bytes) -> bytes:
    return (
        b"%PDF-1.4\n"
        b"%unif-" + unique + b"\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
    )


PERIOD = "2026-04-01"
YEAR = 2026
MONTH = 4


def _upload(client, supplier_id: int, type_id: int, *, unique: bytes) -> int:
    files = {"file": ("d.pdf", io.BytesIO(_pdf(unique)), "application/pdf")}
    data = {"document_type_id": str(type_id), "coverage_period_start": PERIOD}
    res = client.post(f"/api/v1/suppliers/{supplier_id}/documents", files=files, data=data)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _cell(client, supplier_id: int, type_id: int, month: int = MONTH) -> dict:
    """Devuelve la celda del mes indicado para un tipo de documento."""
    res = client.get(f"/api/v1/suppliers/{supplier_id}/compliance?year={YEAR}")
    assert res.status_code == 200, res.text
    for req in res.json()["monthly_requirements"]:
        if req["document_type"]["id"] == type_id:
            return next(c for c in req["cells"] if c["month"] == month)
    raise AssertionError(f"Tipo {type_id} no está en la rejilla mensual")


# ---------------------------------------------------------------------------
# T003 — la celda deriva del documento
# ---------------------------------------------------------------------------


def test_cell_state_derives_from_document(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    doc_id = _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"der")

    cell = _cell(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert cell["type_validated"] is False

    res = client_with_session.post(f"/api/v1/documents/{doc_id}/verify", json={"note": "ok"})
    assert res.status_code == 200, res.text

    cell = _cell(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert cell["type_validated"] is True
    assert cell["status"] == "validated"


# ---------------------------------------------------------------------------
# US1 — validar desde la rejilla y verificar desde documentos son lo mismo
# ---------------------------------------------------------------------------


def _validate(client, supplier_id: int, type_id: int, *, note: str | None = None):
    body: dict = {"document_type_id": type_id, "coverage_period_start": PERIOD}
    if note is not None:
        body["note"] = note
    return client.post(f"/api/v1/suppliers/{supplier_id}/compliance/validate", json=body)


def test_validating_cell_verifies_the_document(
    client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """T009 — el camino de ida: la rejilla escribe en el documento."""
    doc_id = _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"ida")

    res = _validate(client_with_session, seeded_supplier.id, opinion_sat_type.id, note="Cotejado")
    assert res.status_code == 200, res.text
    assert res.json()["document_id"] == doc_id

    doc = client_with_session.get(f"/api/v1/documents/{doc_id}").json()
    assert doc["verified"] is True
    assert doc["verified_by"]["id"] == session_user.id
    assert doc["verified_at"] is not None
    assert doc["verified_note"] == "Cotejado"


def test_verifying_document_validates_the_cell(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    """T010 — el camino de vuelta: documentos escribe y la rejilla lo refleja."""
    doc_id = _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"vta")

    res = client_with_session.post(f"/api/v1/documents/{doc_id}/verify", json={"note": None})
    assert res.status_code == 200, res.text

    cell = _cell(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert cell["type_validated"] is True


def test_cannot_validate_cell_without_document(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    """T011 — FR-005: sin evidencia no hay nada que dar por bueno."""
    res = _validate(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert res.status_code == 422, res.text
    assert res.json()["error"]["details"]["code"] == "no_document_to_validate"


def test_validating_from_grid_is_audited(
    db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """T012 — FR-008: antes de esta feature la validación no dejaba rastro alguno."""
    doc_id = _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"aud")
    assert _validate(client_with_session, seeded_supplier.id, opinion_sat_type.id).status_code == 200

    res = client_with_session.get(f"/api/v1/documents/{doc_id}/history")
    assert res.status_code == 200, res.text
    verified = [i for i in res.json()["items"] if i["action"] == "document.verified"]
    assert len(verified) == 1
    assert verified[0]["actor"]["user"]["id"] == session_user.id


def test_new_version_returns_cell_to_pending(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    """T013 — FR-009: evidencia nueva es evidencia sin revisar.

    Antes de la unificación la marca vivía en la celda y sobrevivía a la carga
    de una versión nueva: la rejilla seguía diciendo "Validado" sobre un archivo
    que nadie había mirado.
    """
    _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"v1")
    assert _validate(client_with_session, seeded_supplier.id, opinion_sat_type.id).status_code == 200
    assert _cell(client_with_session, seeded_supplier.id, opinion_sat_type.id)["type_validated"] is True

    _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"v2")

    cell = _cell(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert cell["type_validated"] is False


# ---------------------------------------------------------------------------
# US2 — retirar la revisión desde cualquiera de las dos pantallas
# ---------------------------------------------------------------------------


def _unvalidate(client, supplier_id: int, type_id: int):
    return client.post(
        f"/api/v1/suppliers/{supplier_id}/compliance/unvalidate",
        json={"document_type_id": type_id, "coverage_period_start": PERIOD},
    )


def _make_user(db_session, *, organization_id: int, email: str, role: str):  # type: ignore[no-untyped-def]
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


def test_unvalidating_cell_clears_the_document(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    """T021 — el reverso que no existía: la validación de celda era irreversible."""
    doc_id = _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"unv")
    assert _validate(client_with_session, seeded_supplier.id, opinion_sat_type.id).status_code == 200

    res = _unvalidate(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert res.status_code == 200, res.text

    doc = client_with_session.get(f"/api/v1/documents/{doc_id}").json()
    assert doc["verified"] is False
    assert _cell(client_with_session, seeded_supplier.id, opinion_sat_type.id)["type_validated"] is False


def test_viewer_cannot_validate_or_unvalidate(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """T022 — FR-007: el rol de solo lectura no marca ni retira por ninguna vía."""
    _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"vw2")
    viewer = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="consultor-unif@test.mx",
        role="viewer",
    )
    viewer_client = _client_as(
        app, user_id=viewer.id, organization_id=session_user.organization_id, role="viewer"
    )

    assert _validate(viewer_client, seeded_supplier.id, opinion_sat_type.id).status_code == 403
    assert _unvalidate(viewer_client, seeded_supplier.id, opinion_sat_type.id).status_code == 403


def test_manager_can_unverify_document(
    app, db_session, client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """T023 — FR-007: única relajación de control de la feature.

    Antes de spec 017 esta llamada respondía 403 para el manager.
    """
    manager = _make_user(
        db_session,
        organization_id=session_user.organization_id,
        email="gestor-unv@test.mx",
        role="manager",
    )
    mgr_client = _client_as(
        app, user_id=manager.id, organization_id=session_user.organization_id, role="manager"
    )
    doc_id = _upload(mgr_client, seeded_supplier.id, opinion_sat_type.id, unique=b"mgr")
    assert mgr_client.post(f"/api/v1/documents/{doc_id}/verify", json={"note": None}).status_code == 200

    res = mgr_client.post(f"/api/v1/documents/{doc_id}/unverify")
    assert res.status_code == 200, res.text
    assert res.json()["verified"] is False


def test_unvalidate_is_idempotent(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    """T024 — retirar lo que no estaba puesto no es un error."""
    _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"idem")
    res = _unvalidate(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert res.status_code == 200, res.text


def test_unvalidate_without_document_is_rejected(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    """El reverso exige evidencia igual que la marca (FR-005)."""
    res = _unvalidate(client_with_session, seeded_supplier.id, opinion_sat_type.id)
    assert res.status_code == 422, res.text
    assert res.json()["error"]["details"]["code"] == "no_document_to_validate"


def test_unvalidating_is_audited(
    client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """T025 — FR-008: el retiro consta, sin borrar el registro de la revisión previa."""
    doc_id = _upload(client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"audu")
    assert _validate(client_with_session, seeded_supplier.id, opinion_sat_type.id).status_code == 200
    assert _unvalidate(client_with_session, seeded_supplier.id, opinion_sat_type.id).status_code == 200

    items = client_with_session.get(f"/api/v1/documents/{doc_id}/history").json()["items"]
    actions = [i["action"] for i in items]
    assert "document.verified" in actions
    assert "document.unverified" in actions
