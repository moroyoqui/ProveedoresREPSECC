"""Schemas for Document (contracts/documents.md spec 001)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from repse.documents.models import DocumentStatus, OcrStatus


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    display_name: str


class FileMeta(BaseModel):
    name: str
    size_bytes: int
    mime_type: str
    sha256: str


class OcrPayload(BaseModel):
    status: OcrStatus
    extracted_rfc: str | None = None
    extracted_issued_at: date | None = None
    extracted_valid_until: date | None = None


class AuditTrace(BaseModel):
    user: UserBrief
    at: datetime


class VerifiedTrace(BaseModel):
    user: UserBrief
    at: datetime
    note: str | None = None


class DocumentAuditBlock(BaseModel):
    added: AuditTrace
    last_updated: AuditTrace | None = None
    validated: VerifiedTrace | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    document_type_id: int
    coverage_period_start: date | None
    coverage_period_end: date | None
    due_date_calculated: date | None
    due_date_effective: date | None
    due_date_override_reason: str | None
    status: DocumentStatus
    verified: bool
    version: int
    is_latest: bool
    file: FileMeta
    ocr: OcrPayload
    audit: DocumentAuditBlock


class DownloadTokenOut(BaseModel):
    token: str
    expires_at: datetime


class VerifyIn(BaseModel):
    note: str | None = None


class HistoryEntry(BaseModel):
    id: int
    action: str
    actor: dict  # {"type": "human", "user": {...}} | {"type": "system"}
    summary: str
    metadata: dict = {}
    occurred_at: datetime


class HistoryPage(BaseModel):
    items: list[HistoryEntry]
    next_cursor: str | None = None
    has_more: bool = False
