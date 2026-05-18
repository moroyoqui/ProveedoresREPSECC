"""Schemas for Supplier (contracts/suppliers.md spec 001)."""

from __future__ import annotations

from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from repse.documents.models import DocumentStatus
from repse.suppliers.models import SupplierStatus

RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")


class SupplierTypeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    origin: str


class SupplierCounts(BaseModel):
    valid: int = 0
    expiring_soon: int = 0
    expired: int = 0
    missing: int = 0


class SupplierIn(BaseModel):
    legal_name: str = Field(..., min_length=3, max_length=255)
    rfc: str = Field(..., min_length=12, max_length=13)
    supplier_type_id: int | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(None, max_length=32)
    notes: str | None = None

    @field_validator("rfc")
    @classmethod
    def _rfc_format(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not RFC_RE.match(normalized):
            raise ValueError("RFC format invalid")
        return normalized


class SupplierPatch(BaseModel):
    legal_name: str | None = Field(None, min_length=3, max_length=255)
    supplier_type_id: int | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(None, max_length=32)
    status: SupplierStatus | None = None
    notes: str | None = None
    # Texto que el usuario debe escribir ("eliminar", case-insensitive, trimmed)
    # cuando el cambio de supplier_type_id elimina documentos del año en curso
    # (FR-005b–d spec 001, T125 addendum).
    confirmation_text: str | None = Field(None, max_length=32)


class AffectedDocumentOut(BaseModel):
    """Resumen de un documento que será eliminado al cambiar el SupplierType."""

    id: int
    document_type: str
    coverage_period: str | None
    due_date_effective: date | None


class SupplierTypeChangePreviewOut(BaseModel):
    """Respuesta de `GET /suppliers/{id}/type-change-preview`."""

    requires_confirmation: bool
    affected_count: int
    affected_documents: list[AffectedDocumentOut] = []


class SupplierListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    legal_name: str
    rfc: str
    supplier_type: SupplierTypeBrief
    contact_name: str | None
    contact_email: EmailStr | None
    status: SupplierStatus
    compliance_percent: int = 0
    counts: SupplierCounts = SupplierCounts()
    created_at: datetime


class SupplierListPage(BaseModel):
    items: list[SupplierListItem]
    next_cursor: str | None = None
    has_more: bool = False


class DocumentSummaryForType(BaseModel):
    id: int | None
    coverage_period_start: date | None
    coverage_period_end: date | None
    due_date_effective: date | None
    status: DocumentStatus | str  # str to allow 'missing'
    verified: bool
    uploaded_at: datetime | None = None


class DocumentByType(BaseModel):
    document_type: dict
    latest: DocumentSummaryForType | None = None
    status_override: str | None = None


class SupplierDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    legal_name: str
    rfc: str
    supplier_type: SupplierTypeBrief
    status: SupplierStatus
    compliance_percent: int = 0
    counts: SupplierCounts = SupplierCounts()
    documents_by_type: list[DocumentByType] = []
    created_at: datetime
