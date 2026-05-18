"""T121 spec 001: alcance del borrado destructivo.

* Versiones históricas archivadas (`is_latest=false`) cuya `due_date_effective`
  caen en el año en curso TAMBIÉN se eliminan.
* Documentos sin `due_date_effective` (NULL) NO se eliminan.
* Documentos con `due_date_effective` fuera del año en curso NO se eliminan.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select


pytestmark = pytest.mark.integration


def _y() -> int:
    return datetime.now(timezone.utc).year


def _make_doc(
    db_session,
    *,
    supplier,
    document_type,
    actor_user_id,
    sha: str,
    due_year: int | None,
    is_latest: bool = True,
    version: int = 1,
):
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    set_current_tenant(supplier.organization_id)
    due = date(due_year, 6, 30) if due_year is not None else None
    cov_start = date(due_year, 4, 1) if due_year is not None else None
    cov_end = date(due_year, 4, 30) if due_year is not None else None
    doc = Document(
        organization_id=supplier.organization_id,
        supplier_id=supplier.id,
        document_type_id=document_type.id,
        coverage_period_start=cov_start,
        coverage_period_end=cov_end,
        due_date_calculated=due,
        due_date_effective=due,
        status=DocumentStatus.VALID,
        version=version,
        is_latest=is_latest,
        file_path=f"scope/{sha[:8]}.pdf",
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


def test_destructive_scope_includes_archived_and_excludes_null_and_other_years(
    client_with_session,
    db_session,
    session_user,
    seeded_supplier,
    opinion_sat_type,
):
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document
    from repse.supplier_types.models import (
        SupplierType,
        SupplierTypeOrigin,
        SupplierTypeStatus,
    )

    set_current_tenant(session_user.organization_id)
    new_type = SupplierType(
        organization_id=session_user.organization_id,
        name="Servicios",
        origin=SupplierTypeOrigin.CUSTOM,
        status=SupplierTypeStatus.ACTIVE,
    )
    db_session.add(new_type)
    db_session.commit()
    db_session.refresh(new_type)

    # Doc archivado, año en curso → DEBE eliminarse.
    archived_current = _make_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha="archcurrent",
        due_year=_y(),
        is_latest=False,
        version=1,
    )
    # Doc latest, año en curso → DEBE eliminarse.
    latest_current = _make_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha="latestcurr",
        due_year=_y(),
        is_latest=True,
        version=2,
    )
    # Doc latest, año anterior → DEBE quedarse.
    last_year_doc = _make_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha="lastyear",
        due_year=_y() - 1,
        is_latest=True,
        version=3,
    )
    # Doc con due_date NULL → DEBE quedarse.
    null_due_doc = _make_doc(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        actor_user_id=session_user.id,
        sha="nulldue",
        due_year=None,
        is_latest=True,
        version=4,
    )

    res = client_with_session.patch(
        f"/api/v1/suppliers/{seeded_supplier.id}",
        json={"supplier_type_id": new_type.id, "confirmation_text": "eliminar"},
    )
    assert res.status_code == 200

    set_current_tenant(session_user.organization_id)
    remaining_ids = {
        d.id
        for d in db_session.execute(
            select(Document).where(Document.supplier_id == seeded_supplier.id)
        ).scalars()
    }
    assert archived_current.id not in remaining_ids
    assert latest_current.id not in remaining_ids
    assert last_year_doc.id in remaining_ids
    assert null_due_doc.id in remaining_ids
