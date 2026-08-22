"""Schemas for the supplier annual compliance grid (contracts/compliance.md)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from repse.document_types.models import Periodicity
from repse.suppliers.models import SupplierStatus


class CellStatus(StrEnum):
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    EXPIRED = "expired"
    MISSING = "missing"
    PENDING = "pending"
    FUTURE = "future"
    NOT_REQUIRED = "not_required"


class DocumentTypeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    periodicity: Periodicity


class SupplierTypeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class SupplierSummaryOut(BaseModel):
    id: int
    legal_name: str
    rfc: str
    supplier_type: SupplierTypeBrief
    status: SupplierStatus
    compliance_percent: int = 0


class CellOut(BaseModel):
    month: int
    status: CellStatus
    document_id: int | None = None
    document_count: int = 0
    coverage_period_start: date | None = None
    type_validated: bool = False


class MonthlyRequirementOut(BaseModel):
    document_type: DocumentTypeBrief
    cells: list[CellOut]


class OneTimeRequirementOut(BaseModel):
    document_type: DocumentTypeBrief
    status: CellStatus
    document_id: int | None = None
    due_date_effective: date | None = None
    # Spec 017: presente también aquí para que los tipos sin periodicidad
    # expongan el mismo dato que las celdas mensuales.
    type_validated: bool = False


class ComplianceGridOut(BaseModel):
    supplier: SupplierSummaryOut
    year: int
    monthly_requirements: list[MonthlyRequirementOut]
    one_time_requirements: list[OneTimeRequirementOut]
