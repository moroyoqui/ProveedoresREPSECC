"""T088 spec 001: "Faltante" se deriva de SupplierType.requirements
(no del catálogo global) — FR-012b.

El servicio ``suppliers.compliance.aggregate`` cuenta como ``missing`` cada
requirement del SupplierType que no tiene Document(is_latest=true). Tipos de
documento canónicos no requeridos por el SupplierType NO deben aparecer.
"""

from __future__ import annotations

from datetime import date

import pytest


pytestmark = pytest.mark.integration


def test_aggregate_counts_only_requirements_of_supplier_type(
    db_session, session_user, seeded_supplier
) -> None:
    """Reemplazar los requirements del SupplierType del proveedor por un único
    tipo y verificar que aggregate.counts.missing == 1, no N (el total
    canónico).
    """
    from sqlalchemy import select

    from repse.db.tenant_filter import set_current_tenant
    from repse.document_types.models import DocumentType
    from repse.supplier_types.models import (
        RequirementStatus,
        SupplierTypeDocumentRequirement,
    )
    from repse.suppliers.compliance import aggregate

    set_current_tenant(session_user.organization_id)

    # Borra todos los requirements del SupplierType del proveedor; deja sólo opinion-sat.
    all_reqs = db_session.execute(
        select(SupplierTypeDocumentRequirement).where(
            SupplierTypeDocumentRequirement.supplier_type_id == seeded_supplier.supplier_type_id
        )
    ).scalars().all()
    for r in all_reqs:
        r.status = RequirementStatus.RETIRED

    opinion_sat = db_session.execute(
        select(DocumentType).where(DocumentType.slug == "opinion-sat")
    ).scalar_one()

    req = SupplierTypeDocumentRequirement(
        organization_id=session_user.organization_id,
        supplier_type_id=seeded_supplier.supplier_type_id,
        document_type_id=opinion_sat.id,
        status=RequirementStatus.ACTIVE,
    )
    db_session.add(req)
    db_session.commit()

    agg = aggregate(db_session, supplier_id=seeded_supplier.id)
    assert agg["counts"]["missing"] == 1
    assert agg["counts"]["valid"] == 0


def test_aggregate_ignores_canonical_types_not_required_by_supplier_type(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    """Un documento subido para un DocumentType que NO está en los requirements
    del SupplierType (caso histórico) no debe inflar ``valid``. Sólo cuentan
    los pares requirement × latest doc.
    """
    from sqlalchemy import select

    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document, DocumentStatus, OcrStatus
    from repse.supplier_types.models import (
        RequirementStatus,
        SupplierTypeDocumentRequirement,
    )
    from repse.suppliers.compliance import aggregate

    set_current_tenant(session_user.organization_id)

    # Deja sólo un requirement activo (opinion-sat) y siembra un doc cubriéndolo.
    reqs = db_session.execute(
        select(SupplierTypeDocumentRequirement).where(
            SupplierTypeDocumentRequirement.supplier_type_id == seeded_supplier.supplier_type_id
        )
    ).scalars().all()
    for r in reqs:
        r.status = (
            RequirementStatus.ACTIVE
            if r.document_type_id == opinion_sat_type.id
            else RequirementStatus.RETIRED
        )
    db_session.add(
        Document(
            organization_id=session_user.organization_id,
            supplier_id=seeded_supplier.id,
            document_type_id=opinion_sat_type.id,
            coverage_period_start=date(2026, 4, 1),
            coverage_period_end=date(2026, 4, 30),
            due_date_calculated=date(2026, 5, 31),
            due_date_effective=date(2026, 5, 31),
            status=DocumentStatus.VALID,
            file_path="x",
            file_name_original="x.pdf",
            file_size_bytes=1,
            file_mime_type="application/pdf",
            file_sha256="a" * 64,
            ocr_status=OcrStatus.NOT_RUN,
            uploaded_by=session_user.id,
        )
    )
    db_session.commit()

    agg = aggregate(db_session, supplier_id=seeded_supplier.id)
    # 1 requirement activo → 1 doc cubriéndolo → valid=1, missing=0.
    assert agg["counts"]["valid"] == 1
    assert agg["counts"]["missing"] == 0
    assert agg["percent"] == 100


def test_supplier_detail_includes_missing_rows_for_uncovered_requirements(
    client_with_session, db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    """``GET /api/v1/suppliers/{id}`` (T095) debe incluir filas sintéticas
    "Faltante" por cada requirement activo sin documento.
    """
    from sqlalchemy import select

    from repse.supplier_types.models import (
        RequirementStatus,
        SupplierTypeDocumentRequirement,
    )

    # Conserva al menos opinion-sat como requirement activo, sin documento subido.
    reqs = db_session.execute(
        select(SupplierTypeDocumentRequirement).where(
            SupplierTypeDocumentRequirement.supplier_type_id == seeded_supplier.supplier_type_id
        )
    ).scalars().all()
    for r in reqs:
        r.status = (
            RequirementStatus.ACTIVE
            if r.document_type_id == opinion_sat_type.id
            else RequirementStatus.RETIRED
        )
    db_session.commit()

    res = client_with_session.get(f"/api/v1/suppliers/{seeded_supplier.id}")
    assert res.status_code == 200, res.text
    body = res.json()

    # Estructura del agregado.
    assert "compliance_percent" in body
    assert "counts" in body
    assert set(body["counts"].keys()) >= {"valid", "expiring_soon", "expired", "missing"}

    # Fila sintética "missing" para opinion-sat.
    rows = body["documents_by_type"]
    sat_rows = [r for r in rows if r["document_type"]["slug"] == "opinion-sat"]
    assert len(sat_rows) == 1
    assert sat_rows[0]["status_override"] == "missing"
    assert sat_rows[0]["latest"] is None
