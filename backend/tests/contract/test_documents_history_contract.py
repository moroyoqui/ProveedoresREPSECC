"""T090 spec 001: contract test para ``GET /documents/{id}/history``.

Confirma:

* La respuesta sigue el shape del contrato (items con ``id``, ``action``,
  ``actor``, ``summary``, ``metadata``, ``occurred_at``).
* Las acciones humanas vienen con ``actor.type == "human"`` + ``actor.user``.
* Las acciones del sistema (p.ej. ``document.ocr_completed``) vienen con
  ``actor.type == "system"`` y sin ``actor.user``.
* 404 cuando el documento no pertenece al tenant del solicitante.
"""

from __future__ import annotations

import io

import pytest


pytestmark = pytest.mark.integration


def _minimal_pdf_bytes(unique: bytes) -> bytes:
    return (
        b"%PDF-1.4\n"
        b"%hist-" + unique + b"\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n99\n%%EOF\n"
    )


def _seed_doc_with_audit(
    db_session,
    *,
    organization_id: int,
    supplier_id: int,
    document_type_id: int,
    uploader_id: int,
    unique: bytes = b"hist",
):
    from datetime import date as _date

    from repse.audit.actions import (
        DOCUMENT_OCR_COMPLETED,
        DOCUMENT_UPLOADED,
        DOCUMENT_VERIFIED,
    )
    from repse.audit.service import AuditEvent, write_event, write_system_event
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    set_current_tenant(organization_id)
    doc = Document(
        organization_id=organization_id,
        supplier_id=supplier_id,
        document_type_id=document_type_id,
        coverage_period_start=_date(2026, 4, 1),
        coverage_period_end=_date(2026, 4, 30),
        due_date_calculated=_date(2026, 5, 31),
        due_date_effective=_date(2026, 5, 31),
        status=DocumentStatus.VALID,
        file_path="x",
        file_name_original="x.pdf",
        file_size_bytes=1,
        file_mime_type="application/pdf",
        file_sha256=(unique.hex() if isinstance(unique, bytes) else unique).ljust(64, "0")[:64],
        ocr_status=OcrStatus.SUCCESS,
        uploaded_by=uploader_id,
    )
    db_session.add(doc)
    db_session.flush()

    write_event(
        db_session,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=uploader_id,
            action=DOCUMENT_UPLOADED,
            entity_type="document",
            entity_id=doc.id,
            metadata={"version": 1},
        ),
    )
    write_system_event(
        db_session,
        organization_id=organization_id,
        action=DOCUMENT_OCR_COMPLETED,
        entity_type="document",
        entity_id=doc.id,
        metadata={"extracted_rfc": "SIN9001022Y3"},
    )
    write_event(
        db_session,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=uploader_id,
            action=DOCUMENT_VERIFIED,
            entity_type="document",
            entity_id=doc.id,
            metadata={"note": "Cotejado con SAT"},
        ),
    )
    db_session.commit()
    db_session.refresh(doc)
    return doc


def test_history_returns_human_and_system_actions(
    client_with_session, db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    doc = _seed_doc_with_audit(
        db_session,
        organization_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        document_type_id=opinion_sat_type.id,
        uploader_id=session_user.id,
        unique=b"hist1",
    )

    res = client_with_session.get(f"/api/v1/documents/{doc.id}/history")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "items" in body
    items = body["items"]
    assert len(items) >= 3

    actions = {item["action"] for item in items}
    assert {"document.uploaded", "document.ocr_completed", "document.verified"} <= actions

    for item in items:
        assert "id" in item
        assert "action" in item
        assert "actor" in item
        assert "summary" in item
        assert "metadata" in item
        assert "occurred_at" in item
        actor = item["actor"]
        assert actor["type"] in {"human", "system"}
        if actor["type"] == "human":
            assert "user" in actor
            assert "id" in actor["user"]
            assert "display_name" in actor["user"]
        else:
            assert actor.get("user") is None

    # OCR siempre es del sistema.
    ocr = next(i for i in items if i["action"] == "document.ocr_completed")
    assert ocr["actor"]["type"] == "system"

    # Subida y verificación humanas.
    uploaded = next(i for i in items if i["action"] == "document.uploaded")
    assert uploaded["actor"]["type"] == "human"
    assert uploaded["actor"]["user"]["id"] == session_user.id


def test_history_filters_actor_type(
    client_with_session, db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    doc = _seed_doc_with_audit(
        db_session,
        organization_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        document_type_id=opinion_sat_type.id,
        uploader_id=session_user.id,
        unique=b"hist2",
    )

    only_system = client_with_session.get(
        f"/api/v1/documents/{doc.id}/history?actor=system"
    )
    assert only_system.status_code == 200
    items = only_system.json()["items"]
    assert items
    assert all(i["actor"]["type"] == "system" for i in items)

    only_human = client_with_session.get(
        f"/api/v1/documents/{doc.id}/history?actor=human"
    )
    assert only_human.status_code == 200
    items = only_human.json()["items"]
    assert items
    assert all(i["actor"]["type"] == "human" for i in items)


def test_history_returns_404_for_other_tenant(
    client_with_session_org_a, client_with_session_org_b, document_in_org_a
) -> None:
    res = client_with_session_org_b.get(
        f"/api/v1/documents/{document_in_org_a.id}/history"
    )
    assert res.status_code == 404
