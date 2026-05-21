"""Portal del proveedor — endpoints para usuarios con rol supplier."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, require_role
from repse.compliance.models import ComplianceCellValidation
from repse.compliance.schemas import ComplianceGridOut
from repse.compliance.service import get_annual_compliance
from repse.config import Settings, get_settings
from repse.db.session import get_db
from repse.db.tenant_filter import set_current_tenant
from repse.documents.models import Document, DocumentStatus
from repse.documents.service import ALLOWED_MIME_TYPES, UploadInput, upload_document
from repse.errors import Conflict, UnprocessableEntity, ValidationFailure
from repse.portal.models import PortalSubmission, PreSubmissionStatus, SubmissionStatus
from repse.portal.schemas import SubmissionDetail, SubmissionOut, SubmitRequest, UploadOut
from repse.users.models import Role

router = APIRouter()

_MIN_YEAR = 2020
_MAX_FILES_PER_CELL = 10


def _current_year() -> int:
    return date.today().year


@router.get("/compliance", response_model=ComplianceGridOut)
def portal_compliance(
    year: int | None = Query(None),
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> ComplianceGridOut:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    effective_year = year if year is not None else _current_year()
    if effective_year < _MIN_YEAR or effective_year > _current_year():
        raise ValidationFailure(
            f"Year must be between {_MIN_YEAR} and {_current_year()}"
        )
    set_current_tenant(user.organization_id)
    return get_annual_compliance(
        db,
        supplier_id=user.supplier_id,
        organization_id=user.organization_id,
        year=effective_year,
        portal_mode=True,
    )


@router.get("/history/{document_type_id}")
def portal_document_history(
    document_type_id: int,
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> list[dict]:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)
    rows = db.execute(
        select(Document)
        .where(
            Document.supplier_id == user.supplier_id,
            Document.document_type_id == document_type_id,
            Document.organization_id == user.organization_id,
            Document.deleted_at.is_(None),
        )
        .order_by(Document.coverage_period_start.desc(), Document.version.desc())
    ).scalars().all()

    return [
        {
            "id": doc.id,
            "version": doc.version,
            "is_latest": doc.is_latest,
            "coverage_period_start": doc.coverage_period_start.isoformat() if doc.coverage_period_start else None,
            "coverage_period_end": doc.coverage_period_end.isoformat() if doc.coverage_period_end else None,
            "due_date_effective": doc.due_date_effective.isoformat() if doc.due_date_effective else None,
            "status": doc.status.value if doc.status else None,
            "file_name_original": doc.file_name_original,
            "uploaded_by": doc.uploaded_by,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in rows
    ]


@router.post("/upload", status_code=201, response_model=UploadOut)
def portal_upload(
    file: UploadFile = File(...),
    document_type_id: int = Form(...),
    coverage_period_start: str | None = Form(None),
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Document:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )

    period_start: date | None = None
    if coverage_period_start:
        period_start = date.fromisoformat(coverage_period_start)

    if period_start is not None:
        today = date.today()
        first_of_month = date(today.year, today.month, 1)
        if period_start > first_of_month:
            raise UnprocessableEntity(
                "Coverage period is in the future",
                details={"code": "future_period"},
            )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise UnprocessableEntity(
            "File type not accepted for this document type",
            details={"code": "invalid_file_type"},
        )

    raw = file.file.read()
    if len(raw) > settings.upload_max_bytes:
        raise UnprocessableEntity(
            "File exceeds maximum allowed size",
            details={"code": "file_too_large"},
        )
    file.file.seek(0)

    set_current_tenant(user.organization_id)

    _check_upload_allowed(
        db,
        organization_id=user.organization_id,
        supplier_id=user.supplier_id,
        document_type_id=document_type_id,
        coverage_period_start=period_start,
    )

    doc_count = db.execute(
        select(func.count(Document.id)).where(
            Document.organization_id == user.organization_id,
            Document.supplier_id == user.supplier_id,
            Document.document_type_id == document_type_id,
            Document.coverage_period_start == period_start,
            Document.deleted_at.is_(None),
        )
    ).scalar_one()
    if doc_count >= _MAX_FILES_PER_CELL:
        raise Conflict(
            "Maximum number of files per cell reached",
            details={"code": "max_files_reached"},
        )

    return upload_document(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        upload=file,
        body=UploadInput(
            supplier_id=user.supplier_id,
            document_type_id=document_type_id,
            coverage_period_start=period_start,
            due_date_override=None,
            due_date_override_reason=None,
        ),
        settings=settings,
    )


@router.post("/submit/{document_type_id}", status_code=201, response_model=SubmissionOut)
def portal_submit(
    document_type_id: int,
    body: SubmitRequest,
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)
    period_start = body.coverage_period_start

    doc_count = db.execute(
        select(func.count(Document.id)).where(
            Document.organization_id == user.organization_id,
            Document.supplier_id == user.supplier_id,
            Document.document_type_id == document_type_id,
            Document.coverage_period_start == period_start,
            Document.deleted_at.is_(None),
        )
    ).scalar_one()
    if doc_count == 0:
        raise Conflict(
            "No documents uploaded for this cell",
            details={"code": "no_documents_uploaded"},
        )

    existing = db.execute(
        select(PortalSubmission).where(
            PortalSubmission.organization_id == user.organization_id,
            PortalSubmission.supplier_id == user.supplier_id,
            PortalSubmission.document_type_id == document_type_id,
            PortalSubmission.coverage_period_start == period_start,
            PortalSubmission.status == SubmissionStatus.PENDING,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict(
            "A submission is already pending for this cell",
            details={"code": "already_submitted"},
        )

    validation = db.execute(
        select(ComplianceCellValidation).where(
            ComplianceCellValidation.organization_id == user.organization_id,
            ComplianceCellValidation.supplier_id == user.supplier_id,
            ComplianceCellValidation.document_type_id == document_type_id,
            ComplianceCellValidation.coverage_period_start == period_start,
        )
    ).scalar_one_or_none()
    if validation is not None:
        raise Conflict(
            "Cell is already validated",
            details={"code": "cell_not_submittable"},
        )

    latest_doc = db.execute(
        select(Document).where(
            Document.organization_id == user.organization_id,
            Document.supplier_id == user.supplier_id,
            Document.document_type_id == document_type_id,
            Document.coverage_period_start == period_start,
            Document.is_latest.is_(True),
            Document.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if latest_doc is not None and latest_doc.status == DocumentStatus.EXPIRING_SOON:
        raise Conflict(
            "Cell status does not allow submission",
            details={"code": "cell_not_submittable"},
        )

    if latest_doc is None:
        pre_status = PreSubmissionStatus.MISSING
    elif latest_doc.status == DocumentStatus.EXPIRED:
        pre_status = PreSubmissionStatus.EXPIRED
    else:
        pre_status = PreSubmissionStatus.PENDING

    submission = PortalSubmission(
        organization_id=user.organization_id,
        supplier_id=user.supplier_id,
        document_type_id=document_type_id,
        coverage_period_start=period_start,
        submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        submitted_by=user.user_id,
        status=SubmissionStatus.PENDING,
        pre_submission_status=pre_status,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return SubmissionOut(
        submission_id=submission.id,
        supplier_id=submission.supplier_id,
        document_type_id=submission.document_type_id,
        coverage_period_start=submission.coverage_period_start,
        submitted_at=submission.submitted_at,
        status=submission.status,
    )


@router.get("/submission/{document_type_id}", response_model=SubmissionDetail | None)
def portal_get_submission(
    document_type_id: int,
    coverage_period_start: date | None = Query(None),
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
) -> SubmissionDetail | None:
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)

    row = db.execute(
        select(PortalSubmission)
        .where(
            PortalSubmission.organization_id == user.organization_id,
            PortalSubmission.supplier_id == user.supplier_id,
            PortalSubmission.document_type_id == document_type_id,
            PortalSubmission.coverage_period_start == coverage_period_start,
        )
        .order_by(PortalSubmission.submitted_at.desc())
    ).scalars().first()

    if row is None:
        return None

    return SubmissionDetail(
        submission_id=row.id,
        status=row.status,
        submitted_at=row.submitted_at,
        rejection_reason=row.rejection_reason,
        rejected_at=row.updated_at if row.status == SubmissionStatus.REJECTED else None,
    )


def _check_upload_allowed(
    db: Session,
    *,
    organization_id: int,
    supplier_id: int,
    document_type_id: int,
    coverage_period_start: date | None,
) -> None:
    """Raise Conflict if the target cell is submitted, validated, or expiring_soon."""
    pending = db.execute(
        select(PortalSubmission).where(
            PortalSubmission.organization_id == organization_id,
            PortalSubmission.supplier_id == supplier_id,
            PortalSubmission.document_type_id == document_type_id,
            PortalSubmission.coverage_period_start == coverage_period_start,
            PortalSubmission.status == SubmissionStatus.PENDING,
        )
    ).scalar_one_or_none()
    if pending is not None:
        raise Conflict(
            "Upload not allowed: cell already submitted for validation",
            details={"code": "upload_not_allowed"},
        )

    validated = db.execute(
        select(ComplianceCellValidation).where(
            ComplianceCellValidation.organization_id == organization_id,
            ComplianceCellValidation.supplier_id == supplier_id,
            ComplianceCellValidation.document_type_id == document_type_id,
            ComplianceCellValidation.coverage_period_start == coverage_period_start,
        )
    ).scalar_one_or_none()
    if validated is not None:
        raise Conflict(
            "Upload not allowed: cell is validated",
            details={"code": "upload_not_allowed"},
        )

    latest_doc = db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.supplier_id == supplier_id,
            Document.document_type_id == document_type_id,
            Document.coverage_period_start == coverage_period_start,
            Document.is_latest.is_(True),
            Document.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if latest_doc is not None and latest_doc.status == DocumentStatus.EXPIRING_SOON:
        raise Conflict(
            "Upload not allowed: document is expiring soon",
            details={"code": "upload_not_allowed"},
        )
