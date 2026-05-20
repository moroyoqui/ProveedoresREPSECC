"""T087 spec 001: cálculo de estado (vigente/expiring_soon/expired) respeta
``expiring_soon_threshold_days`` por organización y se materializa cuando el
threshold cambia (FR-013).
"""

from __future__ import annotations

from datetime import date

import pytest


pytestmark = pytest.mark.integration


def test_compute_status_respects_org_threshold() -> None:
    """``compute_status`` debe usar el threshold parametrizado.

    Documento con due_date a 20 días: con threshold=15 → ``valid``; con
    threshold=30 → ``expiring_soon``.
    """
    from repse.documents.models import Document, DocumentStatus
    from repse.documents.status import compute_status

    today = date(2026, 5, 1)
    doc = Document(
        organization_id=1,
        supplier_id=1,
        document_type_id=1,
        due_date_calculated=date(2026, 5, 21),  # 20 days from today
        status=DocumentStatus.VALID,
        file_path="x",
        file_name_original="x",
        file_size_bytes=1,
        file_mime_type="application/pdf",
        file_sha256="0" * 64,
        uploaded_by=1,
    )

    assert compute_status(doc, today=today, expiring_soon_threshold_days=15) == DocumentStatus.VALID
    assert compute_status(doc, today=today, expiring_soon_threshold_days=30) == DocumentStatus.EXPIRING_SOON


def test_compute_status_expired_when_past_due() -> None:
    from repse.documents.models import Document, DocumentStatus
    from repse.documents.status import compute_status

    today = date(2026, 6, 1)
    doc = Document(
        organization_id=1,
        supplier_id=1,
        document_type_id=1,
        due_date_calculated=date(2026, 5, 31),
        status=DocumentStatus.VALID,
        file_path="x",
        file_name_original="x",
        file_size_bytes=1,
        file_mime_type="application/pdf",
        file_sha256="0" * 64,
        uploaded_by=1,
    )

    assert compute_status(doc, today=today, expiring_soon_threshold_days=15) == DocumentStatus.EXPIRED


def test_recalc_materializes_status_for_organization(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    """Cambiar el ``Document.due_date_effective`` y correr el recalculator debe
    actualizar el campo ``status`` materializado.
    """
    from datetime import date as _date

    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document, DocumentStatus, OcrStatus
    from repse.documents.recalculator import recalc_for_organization

    set_current_tenant(session_user.organization_id)

    # Sembrar documento con status=valid pero due_date ya vencida.
    doc = Document(
        organization_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        document_type_id=opinion_sat_type.id,
        coverage_period_start=_date(2026, 1, 1),
        coverage_period_end=_date(2026, 1, 31),
        due_date_calculated=_date(2026, 2, 28),
        due_date_effective=_date(2026, 2, 28),
        status=DocumentStatus.VALID,  # incorrecto a propósito
        file_path="x",
        file_name_original="x",
        file_size_bytes=1,
        file_mime_type="application/pdf",
        file_sha256="1" * 64,
        ocr_status=OcrStatus.NOT_RUN,
        uploaded_by=session_user.id,
    )
    db_session.add(doc)
    db_session.commit()

    today = _date(2026, 5, 1)
    updated = recalc_for_organization(
        db_session, organization_id=session_user.organization_id, today=today
    )
    assert updated >= 1

    db_session.refresh(doc)
    assert doc.status == DocumentStatus.EXPIRED


def test_changing_org_threshold_flips_status_after_recalc(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    """Aumentar el threshold de la org y recalcular debe convertir un doc
    ``valid`` (con due en N+1 días) en ``expiring_soon`` (FR-013)."""
    from datetime import date as _date

    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.documents.models import Document, DocumentStatus, OcrStatus
    from repse.documents.recalculator import recalc_for_organization
    from repse.organizations.models import Organization

    set_current_tenant(session_user.organization_id)

    today = _date(2026, 5, 1)

    doc = Document(
        organization_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        document_type_id=opinion_sat_type.id,
        coverage_period_start=_date(2026, 4, 1),
        coverage_period_end=_date(2026, 4, 30),
        due_date_calculated=_date(2026, 5, 21),  # 20 days from today
        due_date_effective=_date(2026, 5, 21),
        status=DocumentStatus.VALID,
        file_path="x",
        file_name_original="x",
        file_size_bytes=1,
        file_mime_type="application/pdf",
        file_sha256="2" * 64,
        ocr_status=OcrStatus.NOT_RUN,
        uploaded_by=session_user.id,
    )
    db_session.add(doc)
    db_session.commit()

    # Threshold default = 15. 20 días > 15 → debe quedarse en valid.
    recalc_for_organization(
        db_session, organization_id=session_user.organization_id, today=today
    )
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.VALID

    # Subir threshold a 30 (sin filtro de tenant aquí: la org es global).
    with with_admin_scope():
        org = db_session.get(Organization, session_user.organization_id)
        org.expiring_soon_threshold_days = 30
        db_session.commit()

    recalc_for_organization(
        db_session, organization_id=session_user.organization_id, today=today
    )
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.EXPIRING_SOON
