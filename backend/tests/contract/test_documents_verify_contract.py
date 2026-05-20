"""T089 spec 001: contract tests para verify / unverify.

* ``POST /documents/{id}/verify`` registra ``verified_by``, ``verified_at``,
  ``verified_note`` y actualiza ``last_updated_by`` / ``last_updated_at``.
* ``POST /documents/{id}/unverify`` invierte y queda auditado.

Roles: manager y admin pueden verificar; sólo admin puede unverify (contract).
"""

from __future__ import annotations

import io

import pytest


pytestmark = pytest.mark.integration


def _minimal_pdf_bytes(unique: bytes = b"a") -> bytes:
    # The contract test for upload doesn't care about valid PDF structure for
    # OCR-empty results; we mostly need a unique byte string to avoid sha256
    # collisions across tests.
    return (
        b"%PDF-1.4\n"
        b"%unique-" + unique + b"\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
    )


def _upload_doc(client, supplier_id: int, type_id: int, *, unique: bytes = b"vfy") -> int:
    files = {"file": ("d.pdf", io.BytesIO(_minimal_pdf_bytes(unique)), "application/pdf")}
    data = {"document_type_id": str(type_id), "coverage_period_start": "2026-04-01"}
    res = client.post(f"/api/v1/suppliers/{supplier_id}/documents", files=files, data=data)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_verify_sets_audit_validated_block(
    client_with_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"v1"
    )

    res = client_with_session.post(
        f"/api/v1/documents/{doc_id}/verify",
        json={"note": "Cotejado con portal del SAT"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["verified"] is True
    assert body["verified_note"] == "Cotejado con portal del SAT"
    assert body["verified_at"] is not None

    # FR-011a: bloque "validated" presente, "last_updated" actualizado.
    validated = body["audit"]["validated"]
    assert validated is not None
    assert validated["user"]["id"] == session_user.id
    assert validated["note"] == "Cotejado con portal del SAT"

    last_updated = body["audit"]["last_updated"]
    assert last_updated is not None
    assert last_updated["user"]["id"] == session_user.id


def test_unverify_clears_validation_and_audits(
    client_with_session, seeded_supplier, opinion_sat_type
) -> None:
    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"v2"
    )

    verify = client_with_session.post(
        f"/api/v1/documents/{doc_id}/verify", json={"note": "ok"}
    )
    assert verify.status_code == 200

    unverify = client_with_session.post(f"/api/v1/documents/{doc_id}/unverify")
    assert unverify.status_code == 200, unverify.text
    body = unverify.json()
    assert body["verified"] is False
    assert body["verified_at"] is None
    assert body["verified_note"] is None
    assert body["audit"]["validated"] is None

    # El "last_updated" debe quedar actualizado al usuario que des-verificó
    # (FR-011a/e: la des-verificación es una acción humana).
    assert body["audit"]["last_updated"] is not None


def test_verify_writes_audit_log_entry(
    client_with_session, db_session, seeded_supplier, opinion_sat_type, session_user
) -> None:
    """La acción ``document.verified`` debe persistir en ``audit_log``."""
    from sqlalchemy import select

    from repse.audit.actions import DOCUMENT_VERIFIED
    from repse.audit.models import AuditLog
    from repse.db.tenant_filter import set_current_tenant

    doc_id = _upload_doc(
        client_with_session, seeded_supplier.id, opinion_sat_type.id, unique=b"v3"
    )
    res = client_with_session.post(
        f"/api/v1/documents/{doc_id}/verify", json={"note": "audit-check"}
    )
    assert res.status_code == 200

    set_current_tenant(session_user.organization_id)
    row = db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "document",
            AuditLog.entity_id == doc_id,
            AuditLog.action == DOCUMENT_VERIFIED,
        )
    ).scalar_one_or_none()
    assert row is not None
    assert row.actor_user_id == session_user.id
