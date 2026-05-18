"""Schemas for SupplierType (contracts/supplier-types.md spec 001 — read-only here)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

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


class SupplierTypeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    origin: SupplierTypeOrigin
    status: SupplierTypeStatus
    supplier_count: int
    requirement_count: int


class SupplierTypeDetail(SupplierTypeListItem):
    requirements: list[SupplierTypeRequirementOut] = []
