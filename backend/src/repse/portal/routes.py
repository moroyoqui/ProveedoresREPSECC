"""Portal del proveedor — endpoints de solo lectura para usuarios con rol supplier."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, require_role
from repse.compliance.schemas import ComplianceGridOut
from repse.compliance.service import get_annual_compliance
from repse.db.session import get_db
from repse.db.tenant_filter import set_current_tenant
from repse.documents.models import Document
from repse.errors import Conflict, ValidationFailure
from repse.users.models import Role

router = APIRouter()

_MIN_YEAR = 2020


def _current_year() -> int:
    return date.today().year


@router.get("/compliance", response_model=ComplianceGridOut)
def portal_compliance(
    year: int | None = Query(None),
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> ComplianceGridOut:
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
    return get_annual_compliance(
        db,
        supplier_id=user.supplier_id,
        organization_id=user.organization_id,
        year=effective_year,
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
