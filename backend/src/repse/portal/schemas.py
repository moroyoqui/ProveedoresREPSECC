"""Pydantic schemas for the supplier portal endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from repse.compliance.schemas import ComplianceGridOut
from repse.documents.models import DocumentStatus
from repse.portal.models import SubmissionStatus


class SubmissionOut(BaseModel):
    submission_id: int
    supplier_id: int
    document_type_id: int
    coverage_period_start: date | None
    submitted_at: datetime
    status: SubmissionStatus


class UploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type_id: int
    coverage_period_start: date | None
    coverage_period_end: date | None
    status: DocumentStatus
    file_name_original: str
    file_size_bytes: int
    version: int
    created_at: datetime


class SubmitRequest(BaseModel):
    coverage_period_start: date | None = None


class SubmissionDetail(BaseModel):
    submission_id: int
    status: SubmissionStatus
    submitted_at: datetime
    rejection_reason: str | None
    rejected_at: datetime | None


class _CatalogBrief(BaseModel):
    id: int
    name: str


class PortalComplianceGridOut(ComplianceGridOut):
    """Extends ComplianceGridOut with supplier classification (sector/giro) and REPSE folio."""
    sector: _CatalogBrief | None = None
    giro: _CatalogBrief | None = None
    repse_folio: str | None = None
