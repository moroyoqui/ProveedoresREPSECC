"""Contract tests for supplier type-change destructive flow (T117-T119 spec 001).

Cubre:
  * GET /api/v1/suppliers/{id}/type-change-preview (T117)
  * PATCH /api/v1/suppliers/{id} con/sin documentos afectados (T118)
  * PATCH con confirmation_text válido/inválido (T119)
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Local helpers (DB fixtures inline para no contaminar conftest global)
# ---------------------------------------------------------------------------


def _current_year_tenant() -> int:
    # El tenant test usa la TZ por defecto (America/Mexico_City), basta usar el
    # año UTC actual para fijar documentos en el año en curso.
    return datetime.now(timezone.utc).year


def _other_supplier_type(db_session, organization_id):  # type: ignore[no-untyped-def]
    """Crea un SupplierType custom (distinto a 'Sin clasificar') para cambiar a él."""
    from repse.db.tenant_filter import set_current_tenant
    from repse.supplier_types.models import (
        SupplierType,
        SupplierTypeOrigin,
        SupplierTypeStatus,
    )

    set_current_tenant(organization_id)
    st = SupplierType(
        organization_id=organization_id,
        name="Construcción",
        origin=SupplierTypeOrigin.CUSTOM,
        status=SupplierTypeStatus.ACTIVE,
    )
    db_session.add(st)
    db_session.commit()
    db_session.refresh(st)
    return st


def _seed_document(
    db_session,
    *,
    supplier,
    document_type,
    due_year: int,
    actor_user_id: int,
    file_sha256: str | None = None,
):
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    set_current_tenant(supplier.organization_id)
    sha = file_sha256 or f"{datetime.now(timezone.utc).timestamp():016f}"
    if len(sha) < 64:
        sha = sha.ljust(64, "0")
    doc = Document(
        organization_id=supplier.organization_id,
        supplier_id=supplier.id,
        document_type_id=document_type.id,
        coverage_period_start=date(due_year, 4, 1),
        coverage_period_end=date(due_year, 4, 30),
        due_date_calculated=date(due_year, 5, 31),
        due_date_effective=date(due_year, 5, 31),
        status=DocumentStatus.VALID,
        file_path=f"dummy/{sha[:8]}.pdf",
        file_name_original=f"{sha[:6]}.pdf",
        file_size_bytes=4,
        file_mime_type="application/pdf",
        file_sha256=sha[:64],
        ocr_status=OcrStatus.NOT_RUN,
        uploaded_by=actor_user_id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# T117: preview endpoint
# ---------------------------------------------------------------------------


def test_preview_returns_requires_confirmation_when_docs_in_current_year(
    client_with_session, db_session, session_user, seeded_supplier, opinion_sat_type
):
    new_type = _other_supplier_type(db_session, session_user.organization_id)
    doc = _seed_document(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        due_year=_current_year_tenant(),
        actor_user_id=session_user.id,
        file_sha256="aa" * 32,
    )

    res = client_with_session.get(
        f"/api/v1/suppliers/{seeded_supplier.id}/type-change-preview",
        params={"supplier_type_id": new_type.id},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["requires_confirmation"] is True
    assert body["affected_count"] == 1
    assert body["affected_documents"][0]["id"] == doc.id
    assert body["affected_documents"][0]["document_type"] == "Opinión de cumplimiento SAT"
    assert body["affected_documents"][0]["coverage_period"] is not None
    assert body["affected_documents"][0]["due_date_effective"] is not None


def test_preview_returns_no_confirmation_when_no_docs(
    client_with_session, db_session, session_user, seeded_supplier
):
    new_type = _other_supplier_type(db_session, session_user.organization_id)
    res = client_with_session.get(
        f"/api/v1/suppliers/{seeded_supplier.id}/type-change-preview",
        params={"supplier_type_id": new_type.id},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["requires_confirmation"] is False
    assert body["affected_count"] == 0
    assert body["affected_documents"] == []


def test_preview_other_tenant_returns_404(
    client_with_session_org_a, client_with_session_org_b, supplier_in_org_a, db_session
):
    # Tipos de org B no son visibles desde org A y viceversa.
    from repse.db.tenant_filter import set_current_tenant
    from repse.organizations.models import Organization
    from repse.supplier_types.models import (
        SupplierType,
        SupplierTypeOrigin,
        SupplierTypeStatus,
    )
    from sqlalchemy import select

    org_b = db_session.execute(
        select(Organization).where(Organization.legal_name == "Org B")
    ).scalar_one()
    set_current_tenant(org_b.id)
    st_b = SupplierType(
        organization_id=org_b.id,
        name="Logística",
        origin=SupplierTypeOrigin.CUSTOM,
        status=SupplierTypeStatus.ACTIVE,
    )
    db_session.add(st_b)
    db_session.commit()

    # Org B no puede previsualizar un supplier de Org A → 404
    res = client_with_session_org_b.get(
        f"/api/v1/suppliers/{supplier_in_org_a.id}/type-change-preview",
        params={"supplier_type_id": st_b.id},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# T118: PATCH sin/conf docs en año en curso
# ---------------------------------------------------------------------------


def test_patch_without_confirmation_returns_409_when_docs_in_year(
    client_with_session, db_session, session_user, seeded_supplier, opinion_sat_type
):
    new_type = _other_supplier_type(db_session, session_user.organization_id)
    _seed_document(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        due_year=_current_year_tenant(),
        actor_user_id=session_user.id,
        file_sha256="bb" * 32,
    )
    res = client_with_session.patch(
        f"/api/v1/suppliers/{seeded_supplier.id}",
        json={"supplier_type_id": new_type.id},
    )
    assert res.status_code == 409
    body = res.json()
    assert body["error"]["code"] == "confirmation_required"
    assert body["error"]["details"]["affected_count"] == 1
    assert body["error"]["details"]["affected_documents"]


def test_patch_without_docs_applies_directly(
    client_with_session, db_session, session_user, seeded_supplier
):
    new_type = _other_supplier_type(db_session, session_user.organization_id)
    res = client_with_session.patch(
        f"/api/v1/suppliers/{seeded_supplier.id}",
        json={"supplier_type_id": new_type.id},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["supplier_type"]["id"] == new_type.id


# ---------------------------------------------------------------------------
# T119: confirmation_text válido vs inválido
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["eliminar", "ELIMINAR", "  Eliminar  "])
def test_patch_with_valid_confirmation_executes_change(
    client_with_session, db_session, session_user, seeded_supplier, opinion_sat_type, text
):
    new_type = _other_supplier_type(db_session, session_user.organization_id)
    _seed_document(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        due_year=_current_year_tenant(),
        actor_user_id=session_user.id,
        file_sha256=text.strip().lower().ljust(64, "c"),
    )
    res = client_with_session.patch(
        f"/api/v1/suppliers/{seeded_supplier.id}",
        json={"supplier_type_id": new_type.id, "confirmation_text": text},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["supplier_type"]["id"] == new_type.id
    # Documentos del año en curso fueron eliminados → counts.missing puede incluir
    # nuevos requirements según el tipo nuevo, pero no debe haber 'valid' del periodo.
    assert body["counts"]["valid"] == 0


def test_patch_with_invalid_confirmation_returns_422(
    client_with_session, db_session, session_user, seeded_supplier, opinion_sat_type
):
    new_type = _other_supplier_type(db_session, session_user.organization_id)
    _seed_document(
        db_session,
        supplier=seeded_supplier,
        document_type=opinion_sat_type,
        due_year=_current_year_tenant(),
        actor_user_id=session_user.id,
        file_sha256="dd" * 32,
    )
    res = client_with_session.patch(
        f"/api/v1/suppliers/{seeded_supplier.id}",
        json={"supplier_type_id": new_type.id, "confirmation_text": "eliminame por favor"},
    )
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "invalid_confirmation"
