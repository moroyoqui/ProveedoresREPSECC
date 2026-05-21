"""Annual supplier compliance grid service (spec 006).

Computes the 12-month grid of cell statuses for every active requirement of
the supplier's SupplierType, plus a separate list of one-time (periodicity =
'none') requirements.

All public functions are pure and synchronous; the orchestrating
`get_annual_compliance(...)` performs exactly two read-only queries.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session

from repse.compliance.models import ComplianceCellValidation
from repse.compliance.schemas import (
    CellOut,
    CellStatus,
    ComplianceGridOut,
    DocumentTypeBrief,
    MonthlyRequirementOut,
    OneTimeRequirementOut,
    SupplierSummaryOut,
    SupplierTypeBrief,
)
from repse.portal.models import PortalSubmission, SubmissionStatus
from repse.document_types.models import DocumentType, Periodicity
from repse.documents.models import Document, DocumentStatus
from repse.errors import NotFound
from repse.suppliers.models import Supplier
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierType,
    SupplierTypeDocumentRequirement,
)


_APPLICABLE_MONTHS: dict[Periodicity, list[int]] = {
    Periodicity.MONTHLY: list(range(1, 13)),
    Periodicity.BIMONTHLY: [1, 3, 5, 7, 9, 11],
    Periodicity.ANNUAL: [1],
    Periodicity.NONE: [],
}


def applicable_months(periodicity: Periodicity) -> list[int]:
    """Return the list of months that start a coverage period for `periodicity`."""
    return list(_APPLICABLE_MONTHS[periodicity])


def effective_periodicity(req: Any, document_type: Any) -> Periodicity:
    """Resolve the periodicity for a requirement (override beats the doc-type default)."""
    return req.periodicity_override or document_type.periodicity


def cell_status(
    doc: Any | None,
    *,
    month: int,
    year: int,
    today: date,
    due_month_offset: int = 0,
    portal_mode: bool = False,
) -> CellStatus:
    """Compute a single cell's status (see data-model.md §cell_status).

    ``due_month_offset`` extends the pending window beyond the coverage start
    month. For bimonthly documents the period starts on month S and is due on
    S+2, so pass ``due_month_offset=2`` to keep the cell as PENDING until the
    due month has passed.

    When ``portal_mode=True``, a valid document without a PortalSubmission shows
    as PENDING (uploaded, awaiting explicit submission) instead of SUBMITTED.
    """
    if doc is not None:
        doc_status = doc.status
        # Accept both StrEnum and plain str ("valid", "expired", …).
        if hasattr(doc_status, "value"):
            doc_status = doc_status.value
        if doc_status == DocumentStatus.EXPIRED.value:
            return CellStatus.EXPIRED
        return CellStatus.PENDING if portal_mode else CellStatus.SUBMITTED

    cell_start = date(year, month, 1)
    today_month_start = date(today.year, today.month, 1)
    if cell_start > today_month_start:
        return CellStatus.FUTURE

    if due_month_offset > 0:
        raw_due = month + due_month_offset
        if raw_due <= 12:
            due_month_start = date(year, raw_due, 1)
        else:
            due_month_start = date(year + 1, raw_due - 12, 1)
        if today_month_start <= due_month_start:
            return CellStatus.PENDING
        return CellStatus.MISSING

    if cell_start == today_month_start:
        return CellStatus.PENDING
    return CellStatus.MISSING


def _coverage_start(month: int, year: int) -> date:
    return date(year, month, 1)


def get_annual_compliance(
    db: Session,
    *,
    supplier_id: int,
    organization_id: int,
    year: int,
    today: date | None = None,
    portal_mode: bool = False,
) -> ComplianceGridOut:
    """Build the annual compliance grid for the given supplier and year.

    Raises NotFound if the supplier does not exist or belongs to another tenant
    (the TenantOwned mixin's filter already enforces the latter, but we double
    check the organization_id to keep the 404 path explicit).
    """
    today = today or date.today()

    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.organization_id != organization_id:
        raise NotFound("Supplier not found")

    supplier_type = db.get(SupplierType, supplier.supplier_type_id)

    requirements = db.execute(
        select(SupplierTypeDocumentRequirement, DocumentType)
        .join(DocumentType, DocumentType.id == SupplierTypeDocumentRequirement.document_type_id)
        .where(
            SupplierTypeDocumentRequirement.supplier_type_id == supplier.supplier_type_id,
            SupplierTypeDocumentRequirement.organization_id == organization_id,
            SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
        )
        .order_by(DocumentType.name)
    ).all()

    docs = db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.supplier_id == supplier_id,
            Document.is_latest.is_(True),
            Document.deleted_at.is_(None),
            extract("year", Document.coverage_period_start) == year,
        )
    ).scalars().all()

    docs_by_type_and_month: dict[tuple[int, int], Document] = {}
    docs_by_type_no_period: dict[int, Document] = {}
    for d in docs:
        if d.coverage_period_start is None:
            docs_by_type_no_period[d.document_type_id] = d
        else:
            key = (d.document_type_id, d.coverage_period_start.month)
            docs_by_type_and_month[key] = d

    # Count all non-deleted documents (including non-latest) per (type, month)
    count_rows = db.execute(
        select(
            Document.document_type_id,
            extract("month", Document.coverage_period_start).label("m"),
            func.count().label("cnt"),
        )
        .where(
            Document.organization_id == organization_id,
            Document.supplier_id == supplier_id,
            Document.deleted_at.is_(None),
            extract("year", Document.coverage_period_start) == year,
        )
        .group_by(Document.document_type_id, extract("month", Document.coverage_period_start))
    ).all()
    count_by_type_and_month: dict[tuple[int, int], int] = {
        (int(r.document_type_id), int(r.m)): int(r.cnt) for r in count_rows
    }

    # Load pending portal submissions for this supplier/year (Decision 10 — research.md).
    # Cells with a pending submission display as SUBMITTED regardless of document state.
    pending_submission_rows = db.execute(
        select(
            PortalSubmission.document_type_id,
            PortalSubmission.coverage_period_start,
        ).where(
            PortalSubmission.organization_id == organization_id,
            PortalSubmission.supplier_id == supplier_id,
            PortalSubmission.status == SubmissionStatus.PENDING,
            or_(
                extract("year", PortalSubmission.coverage_period_start) == year,
                PortalSubmission.coverage_period_start.is_(None),
            ),
        )
    ).all()
    pending_submissions: set[tuple[int, date | None]] = {
        (int(r.document_type_id), r.coverage_period_start)
        for r in pending_submission_rows
    }

    # Load type-level validations for the supplier (bulk, one query).
    # Keys: (document_type_id, coverage_period_start) where period is a date or None.
    validation_rows = db.execute(
        select(
            ComplianceCellValidation.document_type_id,
            ComplianceCellValidation.coverage_period_start,
        ).where(
            ComplianceCellValidation.organization_id == organization_id,
            ComplianceCellValidation.supplier_id == supplier_id,
        )
    ).all()
    validated_cells: set[tuple[int, date | None]] = {
        (int(r.document_type_id), r.coverage_period_start) for r in validation_rows
    }

    # Also pick up one-time documents (periodicity 'none' can have NULL coverage
    # period). We need to fetch them in a separate query because the WHERE above
    # filters by extract("year", coverage_period_start) which excludes NULLs.
    one_time_doc_type_ids = [dt.id for _, dt in requirements if dt.periodicity == Periodicity.NONE]
    if one_time_doc_type_ids:
        extra_docs = db.execute(
            select(Document).where(
                Document.organization_id == organization_id,
                Document.supplier_id == supplier_id,
                Document.is_latest.is_(True),
                Document.deleted_at.is_(None),
                Document.document_type_id.in_(one_time_doc_type_ids),
            )
        ).scalars().all()
        for d in extra_docs:
            docs_by_type_no_period.setdefault(d.document_type_id, d)

    monthly: list[MonthlyRequirementOut] = []
    one_time: list[OneTimeRequirementOut] = []

    for req, dt in requirements:
        periodicity = effective_periodicity(req, dt)
        brief = DocumentTypeBrief(
            id=dt.id, slug=dt.slug, name=dt.name, periodicity=dt.periodicity
        )

        if periodicity == Periodicity.NONE:
            doc = docs_by_type_no_period.get(dt.id)
            raw_status = cell_status(doc, month=1, year=year, today=today, portal_mode=portal_mode)
            is_pending = (dt.id, None) in pending_submissions
            final_status = CellStatus.SUBMITTED if is_pending else raw_status
            one_time.append(
                OneTimeRequirementOut(
                    document_type=brief,
                    status=final_status,
                    document_id=doc.id if doc else None,
                    due_date_effective=doc.due_date_effective if doc else None,
                )
            )
            continue

        months = set(applicable_months(periodicity))
        due_offset = 2 if periodicity == Periodicity.BIMONTHLY else 0
        cells: list[CellOut] = []
        for month in range(1, 13):
            if month not in months:
                cells.append(
                    CellOut(
                        month=month,
                        status=CellStatus.NOT_REQUIRED,
                        document_id=None,
                        coverage_period_start=None,
                    )
                )
                continue
            doc = docs_by_type_and_month.get((dt.id, month))
            period_start = _coverage_start(month, year)
            is_type_validated = (dt.id, period_start) in validated_cells
            is_pending = (dt.id, period_start) in pending_submissions
            raw_status = cell_status(
                doc, month=month, year=year, today=today,
                due_month_offset=due_offset, portal_mode=portal_mode,
            )
            if is_type_validated:
                final_status = CellStatus.VALIDATED
            elif is_pending:
                final_status = CellStatus.SUBMITTED
            else:
                final_status = raw_status
            cells.append(
                CellOut(
                    month=month,
                    status=final_status,
                    document_id=doc.id if doc else None,
                    document_count=count_by_type_and_month.get((dt.id, month), 0),
                    coverage_period_start=period_start,
                    type_validated=is_type_validated,
                )
            )
        monthly.append(MonthlyRequirementOut(document_type=brief, cells=cells))

    return ComplianceGridOut(
        supplier=SupplierSummaryOut(
            id=supplier.id,
            legal_name=supplier.legal_name,
            rfc=supplier.rfc,
            supplier_type=SupplierTypeBrief(
                id=supplier_type.id, name=supplier_type.name
            )
            if supplier_type
            else SupplierTypeBrief(id=0, name=""),
            status=supplier.status,
            compliance_percent=_compliance_percent(monthly, one_time),
        ),
        year=year,
        monthly_requirements=monthly,
        one_time_requirements=one_time,
    )


def _compliance_percent(
    monthly: list[MonthlyRequirementOut],
    one_time: list[OneTimeRequirementOut],
) -> int:
    """Pct of cells in {validated, submitted} over cells in {validated, submitted, missing, expired}."""
    countable = {CellStatus.VALIDATED, CellStatus.SUBMITTED, CellStatus.MISSING, CellStatus.EXPIRED}
    ok = {CellStatus.VALIDATED, CellStatus.SUBMITTED}

    total = 0
    good = 0
    for req in monthly:
        for cell in req.cells:
            if cell.status in countable:
                total += 1
                if cell.status in ok:
                    good += 1
    for item in one_time:
        if item.status in countable:
            total += 1
            if item.status in ok:
                good += 1

    if total == 0:
        return 0
    return round(good * 100 / total)
