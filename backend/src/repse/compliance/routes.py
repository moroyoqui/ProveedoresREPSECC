"""Compliance routes (spec 006 — GET /api/v1/suppliers/{id}/compliance)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.compliance import service
from repse.compliance.models import ComplianceCellValidation
from repse.compliance.schemas import ComplianceGridOut
from repse.db.session import get_db
from repse.errors import NotFound, ValidationFailure
from repse.suppliers.models import Supplier
from repse.users.models import Role

router = APIRouter()


@router.get(
    "/suppliers/{supplier_id}/compliance",
    response_model=ComplianceGridOut,
)
def get_supplier_compliance(
    supplier_id: int,
    year: int | None = Query(None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> ComplianceGridOut:
    current_year = date.today().year
    effective_year = year if year is not None else current_year

    if effective_year < 2020 or effective_year > current_year:
        raise ValidationFailure(
            "Year out of allowed range",
            details={"code": "invalid_year", "min": 2020, "max": current_year},
        )

    return service.get_annual_compliance(
        db,
        supplier_id=supplier_id,
        organization_id=user.organization_id,
        year=effective_year,
    )


class ValidateCellIn(BaseModel):
    document_type_id: int
    coverage_period_start: date | None = None


@router.post("/suppliers/{supplier_id}/compliance/validate")
def validate_document_type(
    supplier_id: int,
    body: ValidateCellIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> dict:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.organization_id != user.organization_id:
        raise NotFound("Supplier not found")

    existing = db.execute(
        select(ComplianceCellValidation).where(
            ComplianceCellValidation.organization_id == user.organization_id,
            ComplianceCellValidation.supplier_id == supplier_id,
            ComplianceCellValidation.document_type_id == body.document_type_id,
            ComplianceCellValidation.coverage_period_start == body.coverage_period_start,
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if existing is not None:
        existing.validated_by = user.user_id
        existing.validated_at = now
    else:
        db.add(
            ComplianceCellValidation(
                organization_id=user.organization_id,
                supplier_id=supplier_id,
                document_type_id=body.document_type_id,
                coverage_period_start=body.coverage_period_start,
                validated_by=user.user_id,
                validated_at=now,
            )
        )

    db.commit()
    return {"status": "validated", "validated_at": now.isoformat()}
