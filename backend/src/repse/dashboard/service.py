"""Dashboard aggregation service (spec 005).

Foundational pieces implemented here (decision-independent):
- filter normalization (stable order + dedupe) → cache key
- validation (invalid_year / invalid_status)
- reference-date resolution in the tenant timezone (FR-011/FR-012)
- cache integration (FR-021) and empty-state detection (FR-018/FR-019)

The actual counting (pie / by_document_type / kpis / suppliers) lives in
``_compute_aggregate`` and is intentionally NOT finalized yet: how the dashboard's
4-state taxonomy reconciles with the per-supplier detail grid (SC-003) is a
design decision pending confirmation. See the module TODO.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from repse.common.cache import dashboard_cache
from repse.compliance import service as compliance_service
from repse.compliance.schemas import CellStatus, ComplianceGridOut
from repse.dashboard.schemas import (
    DASHBOARD_STATUSES,
    DashboardFilters,
    DashboardOut,
    DocTypeBar,
    Kpis,
    PieSlice,
    SupplierRow,
)
from repse.document_types.models import (
    DocumentType,
    DocumentTypeStatus,
    TenantDocumentTypeSetting,
)
from repse.documents.models import Document, DocumentStatus
from repse.documents.status import compute_status
from repse.errors import ValidationFailure
from repse.organizations.models import Organization
from repse.suppliers.models import Supplier, SupplierStatus

MIN_YEAR = 2020
MAX_YEARS_BACK = 10
EXPIRING_KPI_WINDOW_DAYS = 30

# CellStatus (detail grid) → dashboard 4-state taxonomy. PENDING/FUTURE/
# NOT_REQUIRED are excluded from the pie (they are not in the detail's
# compliance denominator either), guaranteeing SC-003 consistency.
_PRESENT_CELL = {CellStatus.VALIDATED, CellStatus.SUBMITTED}


# --- Filter parsing / normalization (T006) ----------------------------------


def normalize_filters(
    *,
    year: int | None,
    supplier_type: list[int] | None,
    document_type: list[int] | None,
    supplier: list[int] | None,
    status: list[str] | None,
    include_inactive: bool,
    current_year: int,
) -> DashboardFilters:
    """Validate raw query params and produce a normalized DashboardFilters.

    Raises ValidationFailure with code ``invalid_year`` / ``invalid_status``.
    """
    effective_year = year if year is not None else current_year
    if effective_year < MIN_YEAR or effective_year > current_year:
        raise ValidationFailure(
            "Year out of allowed range",
            details={"code": "invalid_year", "min": MIN_YEAR, "max": current_year},
        )

    statuses = _dedupe_sorted_str(status or [])
    unknown = [s for s in statuses if s not in DASHBOARD_STATUSES]
    if unknown:
        raise ValidationFailure(
            "Unknown status filter",
            details={"code": "invalid_status", "allowed": list(DASHBOARD_STATUSES)},
        )

    return DashboardFilters(
        year=effective_year,
        supplier_type_ids=_dedupe_sorted_int(supplier_type or []),
        document_type_ids=_dedupe_sorted_int(document_type or []),
        supplier_ids=_dedupe_sorted_int(supplier or []),
        statuses=statuses,
        include_inactive=bool(include_inactive),
    )


def _dedupe_sorted_int(values: list[int]) -> list[int]:
    return sorted(set(values))


def _dedupe_sorted_str(values: list[str]) -> list[str]:
    return sorted(set(values))


def _cache_key(filters: DashboardFilters) -> tuple:
    """Hashable, order-stable representation of the filters (cache key part)."""
    return (
        filters.year,
        tuple(filters.supplier_type_ids),
        tuple(filters.document_type_ids),
        tuple(filters.supplier_ids),
        tuple(filters.statuses),
        filters.include_inactive,
    )


# --- Reference date / timezone (T007) ----------------------------------------


def resolve_reference_date(
    *, year: int, tz_name: str, now: datetime | None = None
) -> date:
    """Resolve the date passed to compute_status for the filtered year.

    - current year  → today in the tenant timezone (FR-011)
    - past year     → 31-Dec 23:59 of that year, tenant tz (FR-012)
    - future year   → 31-Dec of that year (callers treat as empty; FR-005)
    """
    tz = ZoneInfo(tz_name)
    now_local = (now or datetime.now(tz)).astimezone(tz)
    if year == now_local.year:
        return now_local.date()
    # Past (or future) year: snapshot at end-of-year close.
    return datetime.combine(date(year, 12, 31), time(23, 59), tzinfo=tz).date()


def _tenant_now(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


# --- Available years (T014, partial — decision-independent) -------------------


def available_years(db: Session, *, organization_id: int, current_year: int) -> list[int]:
    """Years with >=1 document for the tenant, plus the current year, newest
    first, capped to the last MAX_YEARS_BACK years (FR-005)."""
    rows = db.execute(
        select(extract("year", Document.coverage_period_start))
        .where(
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
            Document.coverage_period_start.is_not(None),
        )
        .group_by(extract("year", Document.coverage_period_start))
    ).all()
    years = {int(r[0]) for r in rows if r[0] is not None}
    years.add(current_year)
    floor = current_year - MAX_YEARS_BACK + 1
    return sorted((y for y in years if y >= floor), reverse=True)


# --- Public entrypoint --------------------------------------------------------


def get_dashboard(
    db: Session,
    *,
    organization_id: int,
    filters: DashboardFilters,
    now: datetime | None = None,
) -> DashboardOut:
    cached = dashboard_cache.get(organization_id, _cache_key(filters))
    if cached is not None:
        return cached

    org = db.get(Organization, organization_id)
    tz_name = org.timezone if org is not None else "America/Mexico_City"
    tenant_now = now or _tenant_now(tz_name)
    current_year = tenant_now.astimezone(ZoneInfo(tz_name)).year
    ref_date = resolve_reference_date(year=filters.year, tz_name=tz_name, now=tenant_now)

    result = _compute_aggregate(
        db,
        organization_id=organization_id,
        filters=filters,
        ref_date=ref_date,
        tz_name=tz_name,
        current_year=current_year,
        calculated_at=tenant_now,
    )
    dashboard_cache.set(organization_id, _cache_key(filters), result)
    return result


def _select_suppliers(
    db: Session, *, organization_id: int, filters: DashboardFilters
) -> list[Supplier]:
    stmt = select(Supplier).where(
        Supplier.organization_id == organization_id,
        Supplier.deleted_at.is_(None),
    )
    if not filters.include_inactive:
        stmt = stmt.where(Supplier.status == SupplierStatus.ACTIVE)
    if filters.supplier_type_ids:
        stmt = stmt.where(Supplier.supplier_type_id.in_(filters.supplier_type_ids))
    if filters.supplier_ids:
        stmt = stmt.where(Supplier.id.in_(filters.supplier_ids))
    return list(db.execute(stmt.order_by(Supplier.legal_name)).scalars().all())


def _present_doc_states(
    db: Session,
    *,
    organization_id: int,
    document_ids: set[int],
    ref_date: date,
    threshold_days: int,
) -> dict[int, DocumentStatus]:
    """Recompute valid/expiring_soon/expired for present-cell documents.

    The detail grid collapses present non-expired docs into SUBMITTED; the
    dashboard needs the valid vs expiring_soon split, so we recompute each
    present document's status at ref_date with compute_status (research §2).
    """
    if not document_ids:
        return {}
    docs = db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.id.in_(document_ids),
        )
    ).scalars().all()
    return {
        d.id: compute_status(
            d, today=ref_date, expiring_soon_threshold_days=threshold_days
        )
        for d in docs
    }


def _iter_cells(grid: ComplianceGridOut):
    """Yield (document_type_id, name, cell_status, document_id) for every
    countable cell of a supplier grid (monthly + one-time)."""
    for req in grid.monthly_requirements:
        dt = req.document_type
        for cell in req.cells:
            yield dt.id, dt.name, cell.status, cell.document_id
    for item in grid.one_time_requirements:
        dt = item.document_type
        yield dt.id, dt.name, item.status, item.document_id


def _cell_to_dashboard_state(
    cell_status: CellStatus,
    document_id: int | None,
    present_states: dict[int, DocumentStatus],
) -> str | None:
    """Map a detail cell to a dashboard state, or None if not countable."""
    if cell_status == CellStatus.EXPIRED:
        return "expired"
    if cell_status == CellStatus.MISSING:
        return "missing"
    if cell_status in _PRESENT_CELL:
        # Split present non-expired into valid vs expiring_soon.
        doc_state = present_states.get(document_id) if document_id else None
        if doc_state == DocumentStatus.EXPIRED:
            return "expired"
        if doc_state == DocumentStatus.EXPIRING_SOON:
            return "expiring_soon"
        return "valid"
    return None  # pending / future / not_required → excluded


def _hamilton_percentages(counts: dict[str, int]) -> dict[str, int]:
    """Largest-remainder rounding so the four slices sum to exactly 100 (SC-007)."""
    total = sum(counts.values())
    if total == 0:
        return {k: 0 for k in counts}
    raw = {k: v * 100 / total for k, v in counts.items()}
    floors = {k: int(v) for k, v in raw.items()}
    remainder = 100 - sum(floors.values())
    # Distribute remaining units to the largest fractional parts.
    order = sorted(counts, key=lambda k: raw[k] - floors[k], reverse=True)
    for k in order[:remainder]:
        floors[k] += 1
    return floors


def _compute_aggregate(
    db: Session,
    *,
    organization_id: int,
    filters: DashboardFilters,
    ref_date: date,
    tz_name: str,
    current_year: int,
    calculated_at: datetime,
) -> DashboardOut:
    """Build the aggregate snapshot by reusing the per-supplier detail grid
    (guarantees SC-003) and enriching present cells with compute_status."""
    org = db.get(Organization, organization_id)
    threshold = org.expiring_soon_threshold_days if org is not None else 15

    years = available_years(db, organization_id=organization_id, current_year=current_year)

    # Empty-state: tenant has no suppliers at all (ignores filters) → FR-019.
    total_suppliers = db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.organization_id == organization_id,
            Supplier.deleted_at.is_(None),
        )
    ).scalar_one()
    if total_suppliers == 0:
        return _empty(filters, years, calculated_at, "no_suppliers")

    suppliers = _select_suppliers(db, organization_id=organization_id, filters=filters)

    doc_type_filter = set(filters.document_type_ids)
    status_filter = set(filters.statuses)

    pie_counts = {s: 0 for s in DASHBOARD_STATUSES}
    by_type: dict[int, dict] = {}
    supplier_rows: list[SupplierRow] = []
    at_risk = 0
    active_suppliers = 0

    # Pre-compute grids once per supplier (Option A — reuse detail logic).
    grids: list[tuple[Supplier, ComplianceGridOut]] = []
    present_doc_ids: set[int] = set()
    for sup in suppliers:
        grid = compliance_service.get_annual_compliance(
            db,
            supplier_id=sup.id,
            organization_id=organization_id,
            year=filters.year,
            today=ref_date,
        )
        grids.append((sup, grid))
        for _dt_id, _name, cstatus, doc_id in _iter_cells(grid):
            if doc_id and cstatus in _PRESENT_CELL:
                present_doc_ids.add(doc_id)

    present_states = _present_doc_states(
        db,
        organization_id=organization_id,
        document_ids=present_doc_ids,
        ref_date=ref_date,
        threshold_days=threshold,
    )

    for sup, grid in grids:
        if sup.status == SupplierStatus.ACTIVE:
            active_suppliers += 1
        sup_expired = 0
        sup_missing = 0
        for dt_id, name, cstatus, doc_id in _iter_cells(grid):
            if doc_type_filter and dt_id not in doc_type_filter:
                continue
            state = _cell_to_dashboard_state(cstatus, doc_id, present_states)
            if state is None:
                continue
            if status_filter and state not in status_filter:
                continue
            pie_counts[state] += 1
            bucket = by_type.setdefault(
                dt_id,
                {"name": name, "valid": 0, "expiring_soon": 0, "expired": 0, "missing": 0},
            )
            bucket[state] += 1
            if state == "expired":
                sup_expired += 1
            elif state == "missing":
                sup_missing += 1
        if sup.status == SupplierStatus.ACTIVE and (sup_expired or sup_missing):
            at_risk += 1
        supplier_rows.append(
            SupplierRow(
                supplier_id=sup.id,
                legal_name=sup.legal_name,
                rfc=sup.rfc,
                supplier_type=grid.supplier.supplier_type.name or None,
                status=sup.status.value,
                compliance_percent=grid.supplier.compliance_percent,
                expired=sup_expired,
                missing=sup_missing,
            )
        )

    total_cells = sum(pie_counts.values())
    if total_cells == 0:
        return _empty(filters, years, calculated_at, "no_data_for_filters")

    percentages = _hamilton_percentages(pie_counts)
    pie = [
        PieSlice(status=s, count=pie_counts[s], percent=percentages[s])
        for s in DASHBOARD_STATUSES
    ]

    inactive_ids = _inactive_type_ids(
        db, organization_id=organization_id, type_ids=set(by_type)
    )
    by_document_type = [
        DocTypeBar(
            document_type_id=dt_id,
            name=b["name"],
            inactive=dt_id in inactive_ids,
            valid=b["valid"],
            expiring_soon=b["expiring_soon"],
            expired=b["expired"],
            missing=b["missing"],
            compliance_percent=_compliance_pct(b),
        )
        for dt_id, b in sorted(by_type.items(), key=lambda kv: kv[1]["name"])
    ]

    ok_cells = pie_counts["valid"] + pie_counts["expiring_soon"]
    kpis = Kpis(
        global_compliance_percent=round(ok_cells * 100 / total_cells),
        active_suppliers=active_suppliers,
        at_risk_suppliers=at_risk,
        expiring_30d=_count_expiring_30d(
            db, organization_id=organization_id, ref_date=ref_date, filters=filters
        ),
    )

    return DashboardOut(
        filters=filters,
        pie=pie,
        by_document_type=by_document_type,
        kpis=kpis,
        suppliers=supplier_rows,
        available_years=years,
        calculated_at=calculated_at,
        empty_reason=None,
    )


def _inactive_type_ids(
    db: Session, *, organization_id: int, type_ids: set[int]
) -> set[int]:
    """Tipos de documento inactivos para el tenant: archivados (cualquier
    origen) o canónicos desactivados vía TenantDocumentTypeSetting (FR-014)."""
    if not type_ids:
        return set()
    archived = {
        int(r[0])
        for r in db.execute(
            select(DocumentType.id).where(
                DocumentType.id.in_(type_ids),
                DocumentType.status == DocumentTypeStatus.ARCHIVED,
            )
        ).all()
    }
    deactivated = {
        int(r[0])
        for r in db.execute(
            select(TenantDocumentTypeSetting.document_type_id).where(
                TenantDocumentTypeSetting.organization_id == organization_id,
                TenantDocumentTypeSetting.document_type_id.in_(type_ids),
                TenantDocumentTypeSetting.active.is_(False),
            )
        ).all()
    }
    return archived | deactivated


def _compliance_pct(bucket: dict) -> int:
    ok = bucket["valid"] + bucket["expiring_soon"]
    total = ok + bucket["expired"] + bucket["missing"]
    return round(ok * 100 / total) if total else 0


def _count_expiring_30d(
    db: Session, *, organization_id: int, ref_date: date, filters: DashboardFilters
) -> int:
    """Latest, non-deleted documents whose effective due date falls within the
    next 30 days of ref_date (FR-004). Independent of the org threshold."""
    from datetime import timedelta

    window_end = ref_date + timedelta(days=EXPIRING_KPI_WINDOW_DAYS)
    due = func.coalesce(Document.due_date_effective, Document.due_date_calculated)
    stmt = select(func.count(Document.id)).where(
        Document.organization_id == organization_id,
        Document.is_latest.is_(True),
        Document.deleted_at.is_(None),
        due.is_not(None),
        due >= ref_date,
        due <= window_end,
    )
    if filters.document_type_ids:
        stmt = stmt.where(Document.document_type_id.in_(filters.document_type_ids))
    if filters.supplier_ids:
        stmt = stmt.where(Document.supplier_id.in_(filters.supplier_ids))
    return int(db.execute(stmt).scalar_one())


def _empty(
    filters: DashboardFilters,
    years: list[int],
    calculated_at: datetime,
    reason: str,
) -> DashboardOut:
    return DashboardOut(
        filters=filters,
        pie=[],
        by_document_type=[],
        kpis=Kpis(
            global_compliance_percent=0,
            active_suppliers=0,
            at_risk_suppliers=0,
            expiring_30d=0,
        ),
        suppliers=[],
        available_years=years,
        calculated_at=calculated_at,
        empty_reason=reason,
    )
