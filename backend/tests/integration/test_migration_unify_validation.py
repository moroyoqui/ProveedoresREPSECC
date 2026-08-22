"""Spec 017: la migración que alinea el histórico divergente.

La migración 0013 traslada las validaciones de celda al documento vigente. Se
prueba aquí la **lógica SQL** que ejecuta, sobre datos construidos a propósito,
en lugar de invocar Alembic: las migraciones ya corrieron al crear el esquema de
la sesión de test, y lo que importa verificar es que el traslado respeta la
autoría, no pisa lo ya verificado y no cruza organizaciones.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text


pytestmark = pytest.mark.integration


# SQL idéntico al de backend/alembic/versions/0013_unify_cell_validation_into_documents.py
_MIGRATE_SQL = """
    UPDATE documents d
    JOIN compliance_cell_validations v
         ON d.organization_id = v.organization_id
        AND d.supplier_id = v.supplier_id
        AND d.document_type_id = v.document_type_id
        AND (d.coverage_period_start <=> v.coverage_period_start)
    SET d.verified = 1,
        d.verified_by = v.validated_by,
        d.verified_at = v.validated_at
    WHERE v.organization_id = :org_id
      AND d.is_latest = 1
      AND d.deleted_at IS NULL
      AND d.verified = 0
"""

_ORPHANS_SQL = """
    SELECT v.id
    FROM compliance_cell_validations v
    LEFT JOIN documents d
           ON d.organization_id = v.organization_id
          AND d.supplier_id = v.supplier_id
          AND d.document_type_id = v.document_type_id
          AND (d.coverage_period_start <=> v.coverage_period_start)
          AND d.is_latest = 1
          AND d.deleted_at IS NULL
    WHERE v.organization_id = :org_id
      AND d.id IS NULL
"""

PERIOD = date(2026, 4, 1)
VALIDATED_AT = datetime(2026, 6, 8, 16, 56, 14)


def _add_validation(db_session, *, org_id, supplier_id, type_id, validated_by, period=PERIOD):
    from repse.compliance.models import ComplianceCellValidation
    from repse.db.tenant_filter import with_admin_scope

    with with_admin_scope():
        row = ComplianceCellValidation(
            organization_id=org_id,
            supplier_id=supplier_id,
            document_type_id=type_id,
            coverage_period_start=period,
            validated_by=validated_by,
            validated_at=VALIDATED_AT,
        )
        db_session.add(row)
        db_session.commit()
    return row


def _add_document(
    db_session, *, org_id, supplier_id, type_id, uploaded_by, verified=False, verified_by=None
):
    from repse.db.tenant_filter import with_admin_scope
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    with with_admin_scope():
        doc = Document(
            organization_id=org_id,
            supplier_id=supplier_id,
            document_type_id=type_id,
            coverage_period_start=PERIOD,
            coverage_period_end=date(2026, 4, 30),
            due_date_calculated=date(2026, 5, 17),
            due_date_effective=date(2026, 5, 17),
            status=DocumentStatus.VALID,
            version=1,
            is_latest=True,
            file_path=f"mig/{supplier_id}-{type_id}.pdf",
            file_name_original="d.pdf",
            file_size_bytes=10,
            file_mime_type="application/pdf",
            file_sha256=f"{supplier_id:04d}{type_id:04d}" + "0" * 56,
            ocr_status=OcrStatus.NOT_RUN,
            uploaded_by=uploaded_by,
            verified=verified,
            verified_by=verified_by,
            verified_at=datetime.now(timezone.utc).replace(tzinfo=None) if verified else None,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
    return doc


def _run_migration(db_session, org_id: int) -> int:
    from repse.db.tenant_filter import with_admin_scope

    with with_admin_scope():
        result = db_session.execute(text(_MIGRATE_SQL), {"org_id": org_id})
        db_session.commit()
        return result.rowcount or 0


def _orphans(db_session, org_id: int) -> list[int]:
    from repse.db.tenant_filter import with_admin_scope

    with with_admin_scope():
        return [r[0] for r in db_session.execute(text(_ORPHANS_SQL), {"org_id": org_id})]


def _reload(db_session, doc_id: int):
    from repse.db.tenant_filter import with_admin_scope
    from repse.documents.models import Document

    with with_admin_scope():
        db_session.expire_all()
        return db_session.get(Document, doc_id)


# ---------------------------------------------------------------------------
# T031 — traslado conservando autoría y fecha originales
# ---------------------------------------------------------------------------


def test_migration_moves_validation_to_document(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    doc = _add_document(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        type_id=opinion_sat_type.id,
        uploaded_by=session_user.id,
    )
    _add_validation(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        type_id=opinion_sat_type.id,
        validated_by=session_user.id,
    )

    assert _run_migration(db_session, session_user.organization_id) == 1

    migrated = _reload(db_session, doc.id)
    assert migrated.verified is True
    assert migrated.verified_by == session_user.id
    assert migrated.verified_at == VALIDATED_AT


# ---------------------------------------------------------------------------
# T032 — no pisar lo que ya estaba verificado
# ---------------------------------------------------------------------------


def test_migration_does_not_overwrite_already_verified(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    doc = _add_document(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        type_id=opinion_sat_type.id,
        uploaded_by=session_user.id,
        verified=True,
        verified_by=session_user.id,
    )
    original_at = _reload(db_session, doc.id).verified_at

    _add_validation(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        type_id=opinion_sat_type.id,
        validated_by=session_user.id,
    )

    assert _run_migration(db_session, session_user.organization_id) == 0

    untouched = _reload(db_session, doc.id)
    assert untouched.verified_at == original_at
    assert untouched.verified_at != VALIDATED_AT


# ---------------------------------------------------------------------------
# T033 — las validaciones sin documento se detectan para descartarlas
# ---------------------------------------------------------------------------


def test_migration_detects_orphan_validations(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    """Es el caso de las 32 filas de Prov6: marca sin evidencia que la respalde."""
    orphan = _add_validation(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        type_id=opinion_sat_type.id,
        validated_by=session_user.id,
    )

    detected = _orphans(db_session, session_user.organization_id)
    assert orphan.id in detected

    # No crea nada: no hay documento donde poner la marca.
    assert _run_migration(db_session, session_user.organization_id) == 0


# ---------------------------------------------------------------------------
# T034 — la migración no cruza organizaciones
# ---------------------------------------------------------------------------


def test_migration_does_not_cross_tenants(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    from repse.db.tenant_filter import with_admin_scope
    from repse.organizations.models import Organization

    doc = _add_document(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        type_id=opinion_sat_type.id,
        uploaded_by=session_user.id,
    )
    _add_validation(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        type_id=opinion_sat_type.id,
        validated_by=session_user.id,
    )

    with with_admin_scope():
        other = Organization(
            legal_name="Otra Org", rfc="OTR900101AAA", contact_email="otra@test.mx"
        )
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

    # Migrar la organización ajena no toca el documento de la nuestra.
    assert _run_migration(db_session, other.id) == 0
    assert _reload(db_session, doc.id).verified is False

    # Y migrar la propia sí lo alcanza.
    assert _run_migration(db_session, session_user.organization_id) == 1
    assert _reload(db_session, doc.id).verified is True
