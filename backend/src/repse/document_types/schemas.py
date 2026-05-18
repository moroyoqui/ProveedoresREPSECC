"""Schemas for DocumentType (contracts/document-types.md spec 001)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

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


class DocumentTypeList(BaseModel):
    items: list[DocumentTypeOut]
