"""Schemas for SupplierType (contracts/supplier-types.md spec 001 + spec 003 mutations)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from repse.document_types.models import DocumentTypeOrigin, DocumentTypeStatus, Periodicity
from repse.supplier_types.models import RequirementStatus, SupplierTypeOrigin, SupplierTypeStatus


class SupplierTypeDocumentTypeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    periodicity: Periodicity
    origin: DocumentTypeOrigin
    status: DocumentTypeStatus


class SupplierTypeRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type: SupplierTypeDocumentTypeBrief
    periodicity_override: Periodicity | None
    periodicity_effective: Periodicity
    status: RequirementStatus
    created_at: datetime
    updated_at: datetime


class SupplierTypeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    origin: SupplierTypeOrigin
    status: SupplierTypeStatus
    supplier_count: int
    requirement_count: int
    updated_at: datetime


class SupplierTypeDetail(SupplierTypeListItem):
    requirements: list[SupplierTypeRequirementOut] = []


# ---------- Mutations (spec 003) ----------


class SupplierTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str | None = Field(None, max_length=2000)


class SupplierTypePatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    description: str | None = Field(None, max_length=2000)


class ArchiveIn(BaseModel):
    reason: str | None = Field(None, max_length=500)


class RequirementCreate(BaseModel):
    document_type_id: int
    periodicity_override: Periodicity | None = None


class RequirementPatch(BaseModel):
    periodicity_override: Periodicity | None = None
