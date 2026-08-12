"""Dashboard routes (spec 005 — GET /api/v1/dashboard/compliance).

Read-only, tenant-isolated. organization_id is always taken from the
authenticated session, never from query params.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user
from repse.dashboard import service
from repse.dashboard.schemas import DashboardOut
from repse.db.session import get_db

router = APIRouter()


@router.get("/compliance", response_model=DashboardOut)
def get_compliance_dashboard(
    year: int | None = Query(None),
    supplier_type: list[int] = Query(default_factory=list),
    document_type: list[int] = Query(default_factory=list),
    supplier: list[int] = Query(default_factory=list),
    status: list[str] = Query(default_factory=list),
    include_inactive: bool = Query(False),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> DashboardOut:
    current_year = date.today().year
    filters = service.normalize_filters(
        year=year,
        supplier_type=supplier_type,
        document_type=document_type,
        supplier=supplier,
        status=status,
        include_inactive=include_inactive,
        current_year=current_year,
    )
    return service.get_dashboard(
        db, organization_id=user.organization_id, filters=filters
    )
