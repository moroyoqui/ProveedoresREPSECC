"""Portal del proveedor — operaciones de CARGA (escritura).

Spec 013 (FR-009): aquí viven las únicas operaciones del portal que modifican
información: subir archivos y enviar a validación. Lógica movida sin cambios
desde el antiguo `routes.py` (reglas 009 intactas, FR-007).

SEPARACIÓN respecto al back-office (documents/routes.py):
  - Rol requerido: SUPPLIER (portal) vs ADMIN/MANAGER (back-office).
  - El portal valida aquí: período futuro, límite de archivos por celda y estado
    de celda (_check_upload_allowed). El back-office no aplica estas reglas.
  - Ambos llaman a documents/service.upload_document() como capa de servicio
    compartida. Agregar lógica exclusiva de un canal debe quedar en su ruta,
    NO dentro del service.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, require_role
from repse.compliance.cell_locks import check_cell_unlocked
from repse.config import Settings, get_settings
from repse.db.session import get_db
from repse.db.tenant_filter import set_current_tenant
from repse.documents.models import Document, DocumentStatus
from repse.documents.service import UploadInput, delete_document, upload_document
from repse.errors import Conflict, NotFound, UnprocessableEntity
from repse.portal.models import PortalSubmission, PreSubmissionStatus, SubmissionStatus
from repse.portal.schemas import SubmissionOut, SubmitRequest, UploadOut
from repse.users.models import Role

router = APIRouter()

# Tipos permitidos propios del portal — independientes de documents/service.py.
# Actualizar aquí no afecta al back-office y viceversa.
_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_MAX_FILES_PER_CELL = 10


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

    if file.content_type not in _ALLOWED_MIME_TYPES:
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

    # Spec 017: "celda validada" se lee del documento vigente, no de la tabla
    # obsoleta `compliance_cell_validations`. Seguir consultándola dejaría al
    # proveedor reenviar celdas ya validadas, porque las validaciones nuevas ya
    # no se escriben allí.
    validated_doc = db.execute(
        select(Document).where(
            Document.organization_id == user.organization_id,
            Document.supplier_id == user.supplier_id,
            Document.document_type_id == document_type_id,
            Document.coverage_period_start == period_start,
            Document.is_latest.is_(True),
            Document.deleted_at.is_(None),
            Document.verified.is_(True),
        )
    ).scalar_one_or_none()
    if validated_doc is not None:
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


@router.delete("/documents/{document_id}", status_code=204)
def portal_delete_document(
    document_id: int,
    user: CurrentUser = Depends(require_role(Role.SUPPLIER.value)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Elimina un archivo del propio proveedor mientras la celda siga pendiente.

    Se permite borrar siempre que la celda NO haya sido enviada a validación ni
    validada (sin ventana de tiempo: grace_hours=None). El back-office mantiene
    su propio endpoint con la ventana de gracia de 24h (documents/routes.py).
    """
    if user.supplier_id is None:
        raise Conflict(
            "User has no linked supplier",
            details={"code": "supplier_not_linked"},
        )
    set_current_tenant(user.organization_id)

    doc = db.get(Document, document_id)
    if (
        doc is None
        or doc.organization_id != user.organization_id
        or doc.supplier_id != user.supplier_id
        or doc.deleted_at is not None
    ):
        raise NotFound("Document not found")

    check_cell_unlocked(
        db,
        organization_id=user.organization_id,
        supplier_id=user.supplier_id,
        document_type_id=doc.document_type_id,
        coverage_period_start=doc.coverage_period_start,
    )

    delete_document(
        db,
        document_id=document_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        grace_hours=None,
        settings=settings,
        # El proveedor borra por celda, no por autoría: un documento cargado por
        # el back-office para su empresa sigue siendo suyo a estos efectos.
        require_owner=False,
    )
    return Response(status_code=204)


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

    # Spec 017: misma razón que en portal_submit — la marca vive en el documento.
    validated = db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.supplier_id == supplier_id,
            Document.document_type_id == document_type_id,
            Document.coverage_period_start == coverage_period_start,
            Document.is_latest.is_(True),
            Document.deleted_at.is_(None),
            Document.verified.is_(True),
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
