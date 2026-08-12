"""Pydantic v2 schemas for the compliance dashboard (spec 005).

These mirror ``contracts/dashboard-api.md``. No persisted entities are
introduced; ``DashboardOut`` is a transient aggregate, optionally cached.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# The four base states surfaced by the dashboard (spec 001 FR-012 + derived
# 'missing'). Kept as plain strings to match the JSON contract exactly.
DASHBOARD_STATUSES: tuple[str, ...] = ("valid", "expiring_soon", "expired", "missing")


class DashboardFilters(BaseModel):
    """Echo of the effective, normalized filters applied to the aggregate."""

    year: int
    supplier_type_ids: list[int] = []
    document_type_ids: list[int] = []
    supplier_ids: list[int] = []
    statuses: list[str] = []
    include_inactive: bool = False


class PieSlice(BaseModel):
    status: str
    count: int
    percent: int  # Hamilton-rounded so the four slices sum to exactly 100.


class DocTypeBar(BaseModel):
    document_type_id: int
    name: str
    inactive: bool
    valid: int
    expiring_soon: int
    expired: int
    missing: int
    compliance_percent: int


class Kpis(BaseModel):
    global_compliance_percent: int
    active_suppliers: int
    at_risk_suppliers: int
    expiring_30d: int


class SupplierRow(BaseModel):
    supplier_id: int
    legal_name: str
    rfc: str
    supplier_type: str | None
    status: str
    compliance_percent: int
    expired: int
    missing: int


class DashboardOut(BaseModel):
    filters: DashboardFilters
    pie: list[PieSlice]
    by_document_type: list[DocTypeBar]
    kpis: Kpis
    suppliers: list[SupplierRow]
    available_years: list[int]
    calculated_at: datetime
    empty_reason: str | None = None
