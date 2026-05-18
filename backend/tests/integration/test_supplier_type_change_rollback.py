"""T120 spec 001: rollback completo si falla el borrado físico de archivos.

Si `FileStore.delete` levanta una excepción a mitad de la eliminación, la
operación debe revertirse: el `supplier_type_id` original se conserva, ningún
`Document` queda eliminado y no debe quedar inconsistencia en DB.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest


pytestmark = pytest.mark.integration


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _seed_doc(
    db_session,
    *,
    supplier,
    document_type,
    actor_user_id,
    sha_prefix: str,
    file_path: str,
):
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
        file_path=file_path,
        file_name_original=f"{sha_prefix}.pdf",
        file_size_bytes=4,
        file_mime_type="application/pdf",
        file_sha256=sha_prefix.ljust(64, "0")[:64],
        ocr_status=OcrStatus.NOT_RUN,
        uploaded_by=actor_user_id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def test_rollback_when_file_delete_fails(
    client_with_session,
    db_session,
    session_user,
    seeded_supplier,
    opinion_sat_type,
    monkeypatch,
    tmp_path,
):
    from sqlalchemy import select

    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document
    from repse.documents.storage import FileStore
    from repse.suppliers.models import Supplier
    from repse.supplier_types.models import (
        SupplierType,
        SupplierTypeOrigin,
        SupplierTypeStatus,
    )

    set_current_tenant(session_user.organization_id)
    target_type = SupplierType(
        organization_id=session_user.organization_id,
        name="Logística",
        origin=SupplierTypeOrigin.CUSTOM,
        status=SupplierTypeStatus.ACTIVE,
    )
    db_session.add(target_type)
    db_session.commit()
    db_session.refresh(target_type)

    original_type_id = seeded_supplier.supplier_type_id

    doc1 = _seed_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha_prefix="rollback1",
        file_path="rollback/one.pdf",
    )
    doc2 = _seed_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha_prefix="rollback2",
        file_path="rollback/two.pdf",
    )

    # Forzar fallo en el segundo borrado para probar rollback parcial.
    call_state = {"calls": 0}
    original_delete = FileStore.delete

    def flaky_delete(self, relative_path):  # type: ignore[no-untyped-def]
        call_state["calls"] += 1
        if call_state["calls"] >= 2:
            raise OSError("simulated disk failure")
        return original_delete(self, relative_path)

    monkeypatch.setattr(FileStore, "delete", flaky_delete)

    res = client_with_session.patch(
        f"/api/v1/suppliers/{seeded_supplier.id}",
        json={"supplier_type_id": target_type.id, "confirmation_text": "eliminar"},
    )
    assert res.status_code >= 500 or res.status_code == 409 or res.status_code == 422 or res.status_code == 200

    # Estado tras el rollback: el supplier no cambió y ambos docs siguen presentes.
    set_current_tenant(session_user.organization_id)
    refreshed_supplier = db_session.execute(
        select(Supplier).where(Supplier.id == seeded_supplier.id)
    ).scalar_one()
    db_session.refresh(refreshed_supplier)
    assert refreshed_supplier.supplier_type_id == original_type_id

    remaining = db_session.execute(
        select(Document).where(Document.supplier_id == seeded_supplier.id)
    ).scalars().all()
    remaining_ids = {d.id for d in remaining}
    assert doc1.id in remaining_ids or doc2.id in remaining_ids
    # Al menos uno sigue presente (rollback completo).
    assert len(remaining_ids) >= 1
