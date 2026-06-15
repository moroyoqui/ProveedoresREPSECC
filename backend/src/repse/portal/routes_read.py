"""Portal del proveedor — operaciones de CONSULTA (solo lectura).

Spec 013 (FR-009): este módulo solo registra endpoints GET y ninguno de sus
handlers crea, modifica o elimina información. Las operaciones de carga viven
en `routes_write.py`. Lógica movida sin cambios desde el antiguo `routes.py`.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, require_role
from repse.compliance.schemas import ComplianceGridOut  # noqa: F401  (re-export modelo base)
from repse.compliance.service import get_annual_compliance
from repse.config import Settings, get_settings
from repse.db.session import get_db
from repse.db.tenant_filter import set_current_tenant
from repse.documents.models import Document
from repse.documents.routes import _serialize as _serialize_document
from repse.documents.storage import FileStore
from repse.errors import Conflict, NotFound, ValidationFailure
from repse.giros.models import Giro
from repse.portal.models import PortalSubmission, SubmissionStatus
from repse.portal.schemas import PortalComplianceGridOut, SubmissionDetail
from repse.sectors.models import Sector
from repse.suppliers.models import Supplier
from repse.users.models import Role

router = APIRouter()

_MIN_YEAR = 2020


def _current_year() -> int:
    return date.today().year


@router.get("/compliance", response_model=PortalComplianceGridOut)
def portal_compliance(
    year: int | None = Query(None),
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> PortalComplianceGridOut:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    effective_year = year if year is not None else _current_year()
    if effective_year < _MIN_YEAR or effective_year > _current_year():
        raise ValidationFailure(
            f"Year must be between {_MIN_YEAR} and {_current_year()}"
        )
    set_current_tenant(user.organization_id)
    compliance = get_annual_compliance(
        db,
        supplier_id=user.supplier_id,
        organization_id=user.organization_id,
        year=effective_year,
        portal_mode=True,
    )
    supplier = db.get(Supplier, user.supplier_id)
    sector_out = None
    giro_out = None
    repse_folio = None
    if supplier is not None:
        repse_folio = supplier.repse_folio
        if supplier.sector_id is not None:
            sec = db.get(Sector, supplier.sector_id)
            if sec is not None:
                sector_out = {"id": sec.id, "name": sec.name}
        if supplier.giro_id is not None:
            gir = db.get(Giro, supplier.giro_id)
            if gir is not None:
                giro_out = {"id": gir.id, "name": gir.name}
    return PortalComplianceGridOut(
        **compliance.model_dump(),
        sector=sector_out,
        giro=giro_out,
        repse_folio=repse_folio,
    )


@router.get("/history/{document_type_id}")
def portal_document_history(
    document_type_id: int,
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> list[dict]:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)
    rows = db.execute(
        select(Document)
        .where(
            Document.supplier_id == user.supplier_id,
            Document.document_type_id == document_type_id,
            Document.organization_id == user.organization_id,
            Document.deleted_at.is_(None),
        )
        .order_by(Document.coverage_period_start.desc(), Document.version.desc())
    ).scalars().all()

    return [
        {
            "id": doc.id,
            "version": doc.version,
            "is_latest": doc.is_latest,
            "coverage_period_start": doc.coverage_period_start.isoformat() if doc.coverage_period_start else None,
            "coverage_period_end": doc.coverage_period_end.isoformat() if doc.coverage_period_end else None,
            "due_date_effective": doc.due_date_effective.isoformat() if doc.due_date_effective else None,
            "status": doc.status.value if doc.status else None,
            "file_name_original": doc.file_name_original,
            "uploaded_by": doc.uploaded_by,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in rows
    ]


@router.get("/documents")
def portal_list_documents(
    document_type_id: int = Query(...),
    coverage_period_start: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> dict:
    """Lista los archivos del propio proveedor para una celda (spec 013, FR-010).

    Equivalente de solo-lectura del GET /documents administrativo, con el
    supplier forzado al de la sesión: un proveedor jamás puede listar archivos
    de otra empresa.
    """
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)
    stmt = (
        select(Document)
        .where(
            Document.organization_id == user.organization_id,
            Document.supplier_id == user.supplier_id,
            Document.document_type_id == document_type_id,
            Document.deleted_at.is_(None),
        )
        .order_by(Document.created_at.desc())
    )
    if coverage_period_start is not None:
        stmt = stmt.where(Document.coverage_period_start == date.fromisoformat(coverage_period_start))
    else:
        stmt = stmt.where(Document.coverage_period_start.is_(None))
    docs = db.execute(stmt.limit(limit + 1)).scalars().all()
    has_more = len(docs) > limit
    docs = docs[:limit]
    return {
        "items": [_serialize_document(db, d) for d in docs],
        "next_cursor": None,
        "has_more": has_more,
    }


@router.get("/documents/{document_id}/download-token")
def portal_download_token(
    document_id: int,
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Emite un token de descarga solo para archivos del propio proveedor."""
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)
    doc = db.get(Document, document_id)
    if (
        doc is None
        or doc.organization_id != user.organization_id
        or doc.supplier_id != user.supplier_id
    ):
        raise NotFound("Document not found")
    store = FileStore(settings)
    token = store.issue_download_token(
        file_id=doc.id, user_id=user.user_id, organization_id=user.organization_id
    )
    return {
        "token": token,
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=settings.download_token_ttl_seconds)
        ).isoformat(),
    }


@router.get("/submission/{document_type_id}", response_model=SubmissionDetail | None)
def portal_get_submission(
    document_type_id: int,
    coverage_period_start: date | None = Query(None),
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> SubmissionDetail | None:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)

    row = db.execute(
        select(PortalSubmission)
        .where(
            PortalSubmission.organization_id == user.organization_id,
            PortalSubmission.supplier_id == user.supplier_id,
            PortalSubmission.document_type_id == document_type_id,
            PortalSubmission.coverage_period_start == coverage_period_start,
        )
        .order_by(PortalSubmission.submitted_at.desc())
    ).scalars().first()

    if row is None:
        return None

    return SubmissionDetail(
        submission_id=row.id,
        status=row.status,
        submitted_at=row.submitted_at,
        rejection_reason=row.rejection_reason,
        rejected_at=row.updated_at if row.status == SubmissionStatus.REJECTED else None,
    )
