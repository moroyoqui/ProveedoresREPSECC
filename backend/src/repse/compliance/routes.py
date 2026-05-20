"""Compliance routes (spec 006 — GET /api/v1/suppliers/{id}/compliance)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user
from repse.compliance import service
from repse.compliance.schemas import ComplianceGridOut
from repse.db.session import get_db
from repse.errors import ValidationFailure

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
