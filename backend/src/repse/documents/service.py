"""Document upload + lifecycle service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from repse.audit import actions as audit_actions
from repse.audit.service import AuditEvent, write_event, write_system_event
from repse.config import Settings
from repse.documents.expiration import Periodicity as ExpPeriodicity, compute_due_date
from repse.documents.models import Document, DocumentStatus, OcrStatus
from repse.documents.ocr import run_ocr
from repse.documents.status import compute_status
from repse.documents.storage import FileStore
from repse.errors import Conflict, NotFound, ValidationFailure
from repse.document_types.models import DocumentType, Periodicity
from repse.organizations.models import Organization
from repse.suppliers.models import Supplier
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierTypeDocumentRequirement,
)

# Tipos permitidos para carga de archivos. Importado también por portal/routes_write.py.
# Debe mantenerse sincronizado con UPLOAD_MIME_TYPES en frontend/src/lib/uploadConstraints.ts.
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@dataclass(frozen=True)
class UploadInput:
    supplier_id: int
    document_type_id: int
    coverage_period_start: date | None
    due_date_override: date | None
    due_date_override_reason: str | None


def upload_document(
    db: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    upload: UploadFile,
    body: UploadInput,
    settings: Settings,
) -> Document:
    if upload.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationFailure(
            "Unsupported file type",
            details={"code": "unsupported_file", "mime_type": upload.content_type},
        )

    supplier = db.get(Supplier, body.supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")
    doc_type = db.get(DocumentType, body.document_type_id)
    if doc_type is None:
        raise NotFound("DocumentType not found")

    # Verify the DocumentType is required by this supplier's SupplierType
    # (FR-012b). For 'Sin clasificar' the requirement covers all canonical
    # types so this rule still applies.
    required = db.execute(
        select(SupplierTypeDocumentRequirement).where(
            SupplierTypeDocumentRequirement.supplier_type_id == supplier.supplier_type_id,
            SupplierTypeDocumentRequirement.document_type_id == doc_type.id,
            SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if required is None:
        raise Conflict(
            "Document type not required for this supplier's type",
            details={"code": "type_not_required_by_supplier_type"},
        )

    # Determine effective periodicity (override on the requirement wins).
    effective_periodicity_value = (required.periodicity_override or doc_type.periodicity).value
    eff_per = ExpPeriodicity(effective_periodicity_value)

    if eff_per is not ExpPeriodicity.NONE and body.coverage_period_start is None:
        raise ValidationFailure(
            "coverage_period_start required for periodicity != none",
            details={"code": "invalid_period"},
        )

    due_calculated = compute_due_date(body.coverage_period_start, eff_per)
    due_effective = body.due_date_override or due_calculated
    if body.due_date_override and body.due_date_override != due_calculated:
        if not body.due_date_override_reason:
            raise ValidationFailure(
                "Override requires a reason",
                details={"code": "override_requires_reason"},
            )

    # Read file bytes once: needed for sha256 dedup + storage + OCR.
    raw = upload.file.read()
    if len(raw) > settings.upload_max_bytes:
        raise ValidationFailure("File too large", details={"code": "file_too_large"})
    import hashlib

    sha256 = hashlib.sha256(raw).hexdigest()

    existing_doc = db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.supplier_id == body.supplier_id,
            Document.document_type_id == body.document_type_id,
            Document.coverage_period_start == body.coverage_period_start,
            Document.file_sha256 == sha256,
            Document.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing_doc is not None:
        raise Conflict("Identical file already exists", details={"code": "duplicate_file"})

    # Determine version number: max(existing) + 1 within (supplier, type, period).
    prev_latest = db.execute(
        select(Document).where(
            Document.supplier_id == supplier.id,
            Document.document_type_id == doc_type.id,
            Document.coverage_period_start == body.coverage_period_start,
            Document.is_latest.is_(True),
        )
    ).scalar_one_or_none()

    # Insert provisional row to obtain id (for storage path).
    org = db.get(Organization, organization_id)
    threshold = org.expiring_soon_threshold_days if org else 15

    doc = Document(
        organization_id=organization_id,
        supplier_id=supplier.id,
        document_type_id=doc_type.id,
        coverage_period_start=body.coverage_period_start,
        coverage_period_end=_coverage_period_end(body.coverage_period_start, eff_per),
        due_date_calculated=due_calculated,
        due_date_effective=due_effective,
        due_date_override_reason=body.due_date_override_reason,
        status=DocumentStatus.VALID,  # provisional; recomputed below
        version=(prev_latest.version + 1) if prev_latest else 1,
        is_latest=True,
        file_path="pending",
        file_name_original=upload.filename or "uploaded",
        file_size_bytes=len(raw),
        file_mime_type=upload.content_type or "application/octet-stream",
        file_sha256=sha256,
        ocr_status=OcrStatus.PENDING,
        uploaded_by=actor_user_id,
    )
    db.add(doc)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Conflict(
            "Identical file already exists",
            details={"code": "duplicate_file"},
        )

    # Status now that we know dates.
    doc.status = compute_status(doc, today=datetime.now(timezone.utc).date(),
                                 expiring_soon_threshold_days=threshold)

    # Store file. We re-stream the bytes through BytesIO.
    import io

    store = FileStore(settings)
    ext = Path(upload.filename or "").suffix.lstrip(".").lower() or "bin"
    stored = store.save(
        organization_id=organization_id,
        supplier_id=supplier.id,
        document_id=doc.id,
        version=doc.version,
        extension=ext,
        stream=io.BytesIO(raw),
    )
    doc.file_path = stored.relative_path
    doc.file_size_bytes = stored.size_bytes

    # Archive previous version.
    if prev_latest is not None and prev_latest.id != doc.id:
        prev_latest.is_latest = False

    # Best-effort OCR (sync if small, sync for v1; async upgrade later).
    ocr_result = run_ocr(raw, mime_type=doc.file_mime_type, settings=settings)
    if ocr_result.raw_text:
        doc.ocr_status = OcrStatus.SUCCESS
        doc.ocr_raw_text = ocr_result.raw_text
        doc.ocr_extracted_rfc = ocr_result.rfc
        doc.ocr_extracted_issued_at = ocr_result.issued_at
        doc.ocr_extracted_valid_until = ocr_result.valid_until
    else:
        doc.ocr_status = OcrStatus.FAILED

    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=audit_actions.DOCUMENT_UPLOADED,
            entity_type="document",
            entity_id=doc.id,
            metadata={
                "supplier_id": supplier.id,
                "document_type_id": doc_type.id,
                "file_sha256": sha256,
                "version": doc.version,
            },
        ),
    )
    if doc.ocr_status is OcrStatus.SUCCESS:
        write_system_event(
            db,
            organization_id=organization_id,
            action=audit_actions.DOCUMENT_OCR_COMPLETED,
            entity_type="document",
            entity_id=doc.id,
            metadata={
                "extracted_rfc": doc.ocr_extracted_rfc,
                "extracted_issued_at": doc.ocr_extracted_issued_at.isoformat()
                if doc.ocr_extracted_issued_at
                else None,
            },
        )
    db.commit()
    db.refresh(doc)
    return doc


def _coverage_period_end(start: date | None, per: ExpPeriodicity) -> date | None:
    if start is None or per is ExpPeriodicity.NONE:
        return None
    if per is ExpPeriodicity.MONTHLY:
        return _last_day_of_month(start)
    if per is ExpPeriodicity.BIMONTHLY:
        # End of the bimester containing start.
        from calendar import monthrange

        idx = (start.month - 1) // 2  # 0..5
        end_month = (idx + 1) * 2
        return date(start.year, end_month, monthrange(start.year, end_month)[1])
    if per is ExpPeriodicity.ANNUAL:
        return date(start.year, 12, 31)
    return None


def _last_day_of_month(d: date) -> date:
    from calendar import monthrange

    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def verify_document(
    db: Session,
    *,
    document_id: int,
    organization_id: int,
    actor_user_id: int,
    note: str | None,
) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")
    now = datetime.now(timezone.utc)
    doc.verified = True
    doc.verified_by = actor_user_id
    doc.verified_at = now
    doc.verified_note = note
    doc.last_updated_by = actor_user_id
    doc.last_updated_at = now
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=audit_actions.DOCUMENT_VERIFIED,
            entity_type="document",
            entity_id=doc.id,
            metadata={"note": note or ""},
        ),
    )
    db.commit()
    db.refresh(doc)
    return doc


def unverify_document(
    db: Session, *, document_id: int, organization_id: int, actor_user_id: int
) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")
    if not doc.verified:
        return doc
    now = datetime.now(timezone.utc)
    doc.verified = False
    doc.verified_by = None
    doc.verified_at = None
    doc.verified_note = None
    doc.last_updated_by = actor_user_id
    doc.last_updated_at = now
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=audit_actions.DOCUMENT_UNVERIFIED,
            entity_type="document",
            entity_id=doc.id,
            metadata={},
        ),
    )
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(
    db: Session,
    *,
    document_id: int,
    organization_id: int,
    actor_user_id: int,
    grace_hours: int,
    settings: Settings,
    reason: str | None = None,
) -> None:
    """Borra un documento dentro de la ventana de gracia (T098 spec 001).

    Reglas:
      * Sólo si ``now - created_at`` ≤ ``grace_hours``.
      * Borra el archivo físico y deja la fila soft-deleted (``deleted_at``).
      * Si la fila era ``is_latest`` y existe una versión previa para la misma
        ``(supplier, type, period)``, la marca como ``is_latest=True`` para
        mantener la invariante.
      * Auditado como ``document.deleted``.
    """
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")

    now = datetime.now(timezone.utc)
    # Cargado created_at es naive (DateTime sin TZ). Asumimos UTC en MySQL.
    created_at_utc = doc.created_at
    if created_at_utc.tzinfo is None:
        created_at_utc = created_at_utc.replace(tzinfo=timezone.utc)
    elapsed_seconds = (now - created_at_utc).total_seconds()
    if elapsed_seconds > grace_hours * 3600:
        raise Conflict(
            "Delete window expired",
            details={
                "code": "delete_window_expired",
                "grace_hours": grace_hours,
            },
        )

    # Restaurar la versión previa como `latest` si aplica.
    previous_latest_id: int | None = None
    if doc.is_latest:
        prev = db.execute(
            select(Document)
            .where(
                Document.supplier_id == doc.supplier_id,
                Document.document_type_id == doc.document_type_id,
                Document.coverage_period_start == doc.coverage_period_start,
                Document.is_latest.is_(False),
                Document.id != doc.id,
            )
            .order_by(Document.version.desc())
            .limit(1)
        ).scalar_one_or_none()
        if prev is not None:
            prev.is_latest = True
            previous_latest_id = prev.id

    file_path = doc.file_path
    doc.deleted_at = now
    doc.is_latest = False

    # Borra archivo físico (best-effort: si falla, el log de auditoría queda
    # marcando que el registro se borró).
    try:
        from pathlib import Path

        full = Path(settings.upload_root) / file_path
        if full.exists():
            full.unlink()
    except Exception:  # pragma: no cover
        pass

    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=audit_actions.DOCUMENT_DELETED,
            entity_type="document",
            entity_id=doc.id,
            metadata={
                "reason": reason,
                "file_path": file_path,
                "promoted_previous_latest_id": previous_latest_id,
            },
        ),
    )
    db.commit()
