"""Schemas for DocumentType (contracts/document-types.md spec 001 + spec 003 admin)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from repse.document_types.models import DocumentTypeOrigin, DocumentTypeStatus, Periodicity


class DocumentTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None
    periodicity: Periodicity
    origin: DocumentTypeOrigin
    status: DocumentTypeStatus
    active: bool  # effective per-tenant activation (computed)
    updated_at: str | None = None


class DocumentTypeList(BaseModel):
    items: list[DocumentTypeOut]


# ---------- Mutations (spec 003) ----------


class DocumentTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    periodicity: Periodicity


class DocumentTypePatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    periodicity: Periodicity | None = None


class CanonicalToggle(BaseModel):
    active: bool
    reason: str | None = Field(None, max_length=500)
