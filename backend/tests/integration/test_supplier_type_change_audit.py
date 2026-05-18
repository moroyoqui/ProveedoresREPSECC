"""T122 spec 001: registros de auditoría tras un cambio destructivo.

Tras confirmar la operación, `audit_log` debe contener:
  * Un registro `document.deleted_by_supplier_type_change` por cada documento
    eliminado (con `prev_supplier_type_id` y `new_supplier_type_id` en metadata).
  * Un registro `supplier.type_changed` para el proveedor con la misma
    pareja de tipos.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select


pytestmark = pytest.mark.integration


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _seed_doc(db_session, *, supplier, document_type, actor_user_id, sha):
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    set_current_tenant(supplier.organization_id)
    doc = Document(
        organization_id=supplier.organization_id,
        supplier_id=supplier.id,
        document_type_id=document_type.id,
        coverage_period_start=date(_current_year(), 4, 1),
        coverage_period_end=date(_current_year(), 4, 30),
        due_date_calculated=date(_current_year(), 5, 31),
        due_date_effective=date(_current_year(), 5, 31),
        status=DocumentStatus.VALID,
        file_path=f"audit/{sha[:8]}.pdf",
        file_name_original=f"{sha[:6]}.pdf",
        file_size_bytes=4,
        file_mime_type="application/pdf",
        file_sha256=sha.ljust(64, "0")[:64],
        ocr_status=OcrStatus.NOT_RUN,
        uploaded_by=actor_user_id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def test_audit_log_records_deletes_and_type_change(
    client_with_session,
    db_session,
    session_user,
    seeded_supplier,
    opinion_sat_type,
):
    from repse.audit import actions as audit_actions
    from repse.audit.models import AuditLog
    from repse.db.tenant_filter import set_current_tenant
    from repse.supplier_types.models import (
        SupplierType,
        SupplierTypeOrigin,
        SupplierTypeStatus,
    )

    original_type_id = seeded_supplier.supplier_type_id

    set_current_tenant(session_user.organization_id)
    new_type = SupplierType(
        organization_id=session_user.organization_id,
        name="Manufactura",
        origin=SupplierTypeOrigin.CUSTOM,
        status=SupplierTypeStatus.ACTIVE,
    )
    db_session.add(new_type)
    db_session.commit()
    db_session.refresh(new_type)

    doc_a = _seed_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha="audita",
    )
    doc_b = _seed_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha="auditb",
    )

    res = client_with_session.patch(
        f"/api/v1/suppliers/{seeded_supplier.id}",
        json={"supplier_type_id": new_type.id, "confirmation_text": "eliminar"},
    )
    assert res.status_code == 200

    set_current_tenant(session_user.organization_id)

    deletion_logs = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == audit_actions.DOCUMENT_DELETED_BY_SUPPLIER_TYPE_CHANGE,
            AuditLog.entity_type == "document",
        )
    ).scalars().all()
    deleted_doc_ids = {log.entity_id for log in deletion_logs}
    assert doc_a.id in deleted_doc_ids
    assert doc_b.id in deleted_doc_ids

    for log in deletion_logs:
        assert log.metadata_["prev_supplier_type_id"] == original_type_id
        assert log.metadata_["new_supplier_type_id"] == new_type.id

    type_change_logs = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == audit_actions.SUPPLIER_TYPE_CHANGED,
            AuditLog.entity_type == "supplier",
            AuditLog.entity_id == seeded_supplier.id,
        )
    ).scalars().all()
    assert len(type_change_logs) == 1
    meta = type_change_logs[0].metadata_
    assert meta["prev_supplier_type_id"] == original_type_id
    assert meta["new_supplier_type_id"] == new_type.id
    assert meta["destructive"] is True
    assert meta["deleted_document_count"] == 2
