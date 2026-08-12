"""Integration tests: dashboard↔detail consistency (SC-003) and tenant
isolation (SC-006) for the compliance dashboard (spec 005)."""

from __future__ import annotations

from datetime import date

import pytest

pytestmark = pytest.mark.integration


def _seed_doc(db_session, *, org_id, supplier_id, dtype_id, user_id, status, period, due=None):
    from repse.documents.models import Document, DocumentStatus, OcrStatus

    due = due or date(period.year, period.month, 28)
    db_session.add(
        Document(
            organization_id=org_id,
            supplier_id=supplier_id,
            document_type_id=dtype_id,
            coverage_period_start=period,
            coverage_period_end=date(period.year, period.month, 28),
            due_date_calculated=due,
            due_date_effective=due,
            status=status,
            file_path="x",
            file_name_original="x.pdf",
            file_size_bytes=1,
            file_mime_type="application/pdf",
            file_sha256="b" * 64,
            ocr_status=OcrStatus.NOT_RUN,
            uploaded_by=user_id,
        )
    )


def test_dashboard_pie_sums_100_and_rows_match_detail(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    from repse.compliance import service as compliance_service
    from repse.dashboard import service
    from repse.dashboard.schemas import DashboardFilters
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import DocumentStatus

    set_current_tenant(session_user.organization_id)
    _seed_doc(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        dtype_id=opinion_sat_type.id,
        user_id=session_user.id,
        status=DocumentStatus.VALID,
        period=date(2026, 4, 1),
    )
    db_session.commit()

    filters = DashboardFilters(year=2026)
    out = service.get_dashboard(
        db_session, organization_id=session_user.organization_id, filters=filters
    )

    # SC-007.
    assert sum(s.percent for s in out.pie) == 100
    # SC-003: per-supplier compliance_percent equals the detail grid's value.
    grid = compliance_service.get_annual_compliance(
        db_session,
        supplier_id=seeded_supplier.id,
        organization_id=session_user.organization_id,
        year=2026,
    )
    row = next(r for r in out.suppliers if r.supplier_id == seeded_supplier.id)
    assert row.compliance_percent == grid.supplier.compliance_percent


def test_year_filter_scopes_documents(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    """US2: un documento con periodo cubierto en 2024 aparece como vigente al
    filtrar 2024, pero no contamina el año en curso (FR-013/FR-012)."""
    from sqlalchemy import select

    from repse.dashboard import service
    from repse.dashboard.schemas import DashboardFilters
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import DocumentStatus
    from repse.supplier_types.models import (
        RequirementStatus,
        SupplierTypeDocumentRequirement,
    )

    set_current_tenant(session_user.organization_id)

    # Deja sólo opinion-sat como requisito activo del tipo del proveedor.
    reqs = db_session.execute(
        select(SupplierTypeDocumentRequirement).where(
            SupplierTypeDocumentRequirement.supplier_type_id
            == seeded_supplier.supplier_type_id
        )
    ).scalars().all()
    for r in reqs:
        r.status = (
            RequirementStatus.ACTIVE
            if r.document_type_id == opinion_sat_type.id
            else RequirementStatus.RETIRED
        )

    # Vencimiento en 2025 → al cierre de 2024 sigue vigente (snapshot FR-012).
    _seed_doc(
        db_session,
        org_id=session_user.organization_id,
        supplier_id=seeded_supplier.id,
        dtype_id=opinion_sat_type.id,
        user_id=session_user.id,
        status=DocumentStatus.VALID,
        period=date(2024, 4, 1),
        due=date(2025, 3, 31),
    )
    db_session.commit()

    out_2024 = service.get_dashboard(
        db_session,
        organization_id=session_user.organization_id,
        filters=DashboardFilters(year=2024),
    )
    out_now = service.get_dashboard(
        db_session,
        organization_id=session_user.organization_id,
        filters=DashboardFilters(year=date.today().year),
    )

    assert 2024 in out_2024.available_years
    bar_2024 = next(
        b for b in out_2024.by_document_type
        if b.document_type_id == opinion_sat_type.id
    )
    assert bar_2024.valid >= 1

    bar_now = next(
        (b for b in out_now.by_document_type
         if b.document_type_id == opinion_sat_type.id),
        None,
    )
    valid_now = bar_now.valid if bar_now else 0
    assert valid_now < bar_2024.valid  # el doc de 2024 no contamina el año actual


def test_status_filter_keeps_pie_at_100_over_subset(
    db_session, session_user, seeded_supplier, opinion_sat_type
) -> None:
    """US3: con un filtro de estado, el pastel suma 100% del subconjunto y los
    estados no seleccionados quedan en 0 (FR-007/SC-007)."""
    from datetime import date as _date

    from sqlalchemy import select

    from repse.dashboard import service
    from repse.dashboard.schemas import DashboardFilters
    from repse.db.tenant_filter import set_current_tenant
    from repse.documents.models import DocumentStatus
    from repse.supplier_types.models import (
        RequirementStatus,
        SupplierTypeDocumentRequirement,
    )

    set_current_tenant(session_user.organization_id)
    reqs = db_session.execute(
        select(SupplierTypeDocumentRequirement).where(
            SupplierTypeDocumentRequirement.supplier_type_id
            == seeded_supplier.supplier_type_id
        )
    ).scalars().all()
    for r in reqs:
        r.status = (
            RequirementStatus.ACTIVE
            if r.document_type_id == opinion_sat_type.id
            else RequirementStatus.RETIRED
        )
    db_session.commit()

    year = _date.today().year
    out = service.get_dashboard(
        db_session,
        organization_id=session_user.organization_id,
        filters=DashboardFilters(year=year, statuses=["missing"]),
    )
    by_status = {s.status: s for s in out.pie}
    assert sum(s.percent for s in out.pie) == 100
    assert by_status["missing"].percent == 100
    assert by_status["valid"].count == 0
    assert by_status["expired"].count == 0


def test_mutation_bumps_dashboard_cache_version(
    db_session, session_user, seeded_supplier
) -> None:
    """T038/FR-021a: una mutación (baja de proveedor) invalida el cache del
    tablero incrementando la versión del tenant."""
    from repse.common.cache import dashboard_cache
    from repse.db.tenant_filter import set_current_tenant
    from repse.suppliers import service as suppliers_service

    org_id = session_user.organization_id
    set_current_tenant(org_id)
    before = dashboard_cache.version(org_id)

    suppliers_service.deactivate_supplier(
        db_session,
        supplier_id=seeded_supplier.id,
        organization_id=org_id,
        actor_user_id=session_user.id,
    )

    assert dashboard_cache.version(org_id) == before + 1


def test_no_cross_tenant_leakage(
    db_session, session_user, seeded_supplier
) -> None:
    """A second tenant with no suppliers must see no_suppliers, never org A's
    aggregates (SC-006)."""
    from repse.dashboard import service
    from repse.dashboard.schemas import DashboardFilters
    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.organizations.models import Organization

    with with_admin_scope():
        org_b = Organization(
            legal_name="Org B Iso", rfc="OBISO900101AA", contact_email="b@test.mx"
        )
        db_session.add(org_b)
        db_session.commit()
        db_session.refresh(org_b)

    set_current_tenant(org_b.id)
    out = service.get_dashboard(
        db_session, organization_id=org_b.id, filters=DashboardFilters(year=2026)
    )
    assert out.empty_reason == "no_suppliers"
    assert out.suppliers == []
    assert out.pie == []
