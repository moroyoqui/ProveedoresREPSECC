"""Document routes (back-office, spec 001).

SEPARACIÓN respecto al portal del proveedor (portal/routes_write.py):
  - Rol requerido: ADMIN/MANAGER (back-office) vs SUPPLIER (portal).
  - El back-office permite due_date_override y no restringe períodos futuros.
  - Comparte documents/service.upload_document() con el portal. Lógica exclusiva
    de este canal debe quedar aquí, NO dentro del service.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.audit import actions as audit_actions
from repse.audit.models import AuditLog
from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.compliance.cell_locks import check_cell_unlocked
from repse.config import Settings, get_settings
from repse.db.session import get_db
from repse.document_types.models import DocumentType
from repse.documents import service
from repse.documents.models import Document, OcrStatus
from repse.documents.schemas import VerifyIn
from repse.documents.service import UploadInput
from repse.documents.storage import FileStore, InvalidToken, TokenExpired
from repse.errors import Conflict, Forbidden, NotFound, ValidationFailure
from repse.suppliers.models import Supplier
from repse.users.models import Role, User

router = APIRouter()

# Router separado para canjear tokens de descarga: lo usan tanto el back-office
# como el portal del proveedor, por lo que se monta SIN el guard de back-office
# (spec 013); la autorización viene del token firmado + checks por rol abajo.
files_router = APIRouter()


def _file_store(settings: Settings = Depends(get_settings)) -> FileStore:
    return FileStore(settings)


# ---------- Upload ----------


@router.post("/suppliers/{supplier_id}/documents", status_code=201)
def upload_document(
    supplier_id: int,
    file: UploadFile = File(...),
    document_type_id: int = Form(...),
    coverage_period_start: str | None = Form(None),
    due_date_override: str | None = Form(None),
    due_date_override_reason: str | None = Form(None),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    coverage = date.fromisoformat(coverage_period_start) if coverage_period_start else None
    override = date.fromisoformat(due_date_override) if due_date_override else None
    body = UploadInput(
        supplier_id=supplier_id,
        document_type_id=document_type_id,
        coverage_period_start=coverage,
        due_date_override=override,
        due_date_override_reason=due_date_override_reason,
    )
    doc = service.upload_document(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        upload=file,
        body=body,
        settings=settings,
    )
    return _serialize(db, doc, user=user)


@router.get("/documents")
def list_documents(
    supplier_id: int | None = None,
    document_type_id: int | None = None,
    coverage_period_start: str | None = None,
    status: str | None = None,
    verified: bool | None = None,
    q: str | None = None,
    is_latest: bool = True,
    limit: int = 20,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Document).order_by(Document.created_at.desc())
    if supplier_id is not None:
        stmt = stmt.where(Document.supplier_id == supplier_id)
    if document_type_id is not None:
        stmt = stmt.where(Document.document_type_id == document_type_id)
    if coverage_period_start is not None:
        coverage = date.fromisoformat(coverage_period_start)
        stmt = stmt.where(Document.coverage_period_start == coverage)
    if is_latest:
        stmt = stmt.where(Document.is_latest.is_(True))
    if verified is not None:
        stmt = stmt.where(Document.verified.is_(verified))
    if status is not None:
        from repse.documents.models import DocumentStatus

        stmt = stmt.where(Document.status == DocumentStatus(status))
    if q:
        # Join con Supplier para búsqueda libre por nombre de proveedor o slug de tipo
        stmt = stmt.join(Supplier, Supplier.id == Document.supplier_id).where(
            Supplier.legal_name.ilike(f"%{q}%")
        )
    docs = db.execute(stmt.limit(limit + 1)).scalars().all()
    has_more = len(docs) > limit
    docs = docs[:limit]
    return {
        "items": [_serialize(db, d, include_supplier=True, user=user) for d in docs],
        "next_cursor": None,
        "has_more": has_more,
    }


@router.get("/documents/{document_id}")
def get_document(
    document_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")
    return _serialize(db, doc, user=user)


# ---------- Download tokens + serving ----------


@router.post("/documents/{document_id}/download-token")
def issue_download_token(
    document_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
    store: FileStore = Depends(_file_store),
    settings: Settings = Depends(get_settings),
) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")
    token = store.issue_download_token(
        file_id=doc.id, user_id=user.user_id, organization_id=user.organization_id
    )
    return {
        "token": token,
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=settings.download_token_ttl_seconds)
        ).isoformat(),
    }


@files_router.get("/files/{token}", include_in_schema=False)
def download_file(
    token: str,
    inline: bool = False,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
    store: FileStore = Depends(_file_store),
):
    try:
        payload = store.verify_download_token(token)
    except TokenExpired:
        raise HTTPException(status_code=410, detail="token_expired")
    except InvalidToken:
        raise HTTPException(status_code=403, detail="invalid_token")

    if payload.get("organization_id") != user.organization_id:
        raise Forbidden("Token does not belong to this tenant", details={"code": "tenant_mismatch"})

    doc = db.get(Document, payload.get("file_id"))
    # `deleted_at`: spec 016 FR-010 — un token emitido antes del borrado ya no
    # sirve el archivo. Sin esta condición la fila soft-deleted sigue apuntando
    # a un archivo inexistente y la descarga revienta con 500 en vez de 404.
    if (
        doc is None
        or doc.organization_id != user.organization_id
        or doc.deleted_at is not None
    ):
        raise NotFound("Document not found")

    # Spec 013 (FR-010): un proveedor solo puede descargar archivos de su empresa.
    if user.role == Role.SUPPLIER.value and doc.supplier_id != user.supplier_id:
        raise NotFound("Document not found")

    disposition = "inline" if inline else "attachment"
    fh = store.open(doc.file_path)
    return StreamingResponse(
        fh,
        media_type=doc.file_mime_type,
        headers={"Content-Disposition": f'{disposition}; filename="{doc.file_name_original}"'},
    )


# ---------- Verify / unverify ----------


@router.post("/documents/{document_id}/verify")
def verify_document_route(
    document_id: int,
    body: VerifyIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> dict:
    doc = service.verify_document(
        db,
        document_id=document_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        note=body.note,
    )
    return _serialize(db, doc, user=user)


@router.post("/documents/{document_id}/unverify")
def unverify_document_route(
    document_id: int,
    # Spec 017 (FR-007): antes exclusivo de admin. Se abre al manager para que
    # ambas pantallas se comporten igual y quien valida pueda deshacer su error.
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> dict:
    doc = service.unverify_document(
        db,
        document_id=document_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return _serialize(db, doc, user=user)


# ---------- Delete (with grace window) ----------


@router.delete("/documents/{document_id}", status_code=204)
def delete_document_route(
    document_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Borra un documento del back-office (spec 016).

    El admin borra cualquiera; el manager sólo lo que subió él. Las reglas de
    canal (documento verificado, celda bloqueada) se comprueban aquí y no en el
    service, según la convención descrita en portal/routes_write.py.
    """
    doc = db.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise NotFound("Document not found")

    is_owner = doc.uploaded_by == user.user_id
    if user.role != Role.ADMIN.value and not is_owner:
        raise Forbidden(
            "Only the uploader can delete this document",
            details={"code": "not_document_owner"},
        )

    if doc.verified:
        raise Conflict(
            "Delete not allowed: document is verified",
            details={"code": "document_verified"},
        )

    check_cell_unlocked(
        db,
        organization_id=user.organization_id,
        supplier_id=doc.supplier_id,
        document_type_id=doc.document_type_id,
        coverage_period_start=doc.coverage_period_start,
    )

    service.delete_document(
        db,
        document_id=document_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        grace_hours=settings.document_delete_grace_hours,
        settings=settings,
        require_owner=user.role != Role.ADMIN.value,
    )
    return Response(status_code=204)


# ---------- History (audit timeline for one document) ----------


# Spec 017 (FR-011): estos textos se muestran al usuario en el historial, así
# que usan el mismo término que el resto de la interfaz: "validado". Las claves
# de acción (`document.verified`) no cambian — son datos de auditoría ya escritos.
_HUMAN_SUMMARIES: dict[str, str] = {
    audit_actions.DOCUMENT_UPLOADED: "Subió el documento",
    audit_actions.DOCUMENT_VERIFIED: "Marcó como validado",
    audit_actions.DOCUMENT_UNVERIFIED: "Quitó la validación",
    audit_actions.DOCUMENT_DELETED: "Eliminó el documento",
    audit_actions.DOCUMENT_DELETED_BY_SUPPLIER_TYPE_CHANGE: "Eliminado por cambio de tipo de proveedor",
}

_SYSTEM_SUMMARIES: dict[str, str] = {
    audit_actions.DOCUMENT_OCR_COMPLETED: "Sistema · OCR completado",
    audit_actions.DOCUMENTS_STATUS_RECALCULATED: "Sistema · Estado recalculado",
}


def _history_summary(action: str, *, is_human: bool, metadata: dict) -> str:
    if is_human:
        base = _HUMAN_SUMMARIES.get(action, action)
        if action == audit_actions.DOCUMENT_UPLOADED and metadata.get("version"):
            return f"Subió la versión {metadata['version']}"
        return base
    return _SYSTEM_SUMMARIES.get(action, f"Sistema · {action}")


@router.get("/documents/{document_id}/history")
def get_document_history(
    document_id: int,
    actor: str = Query("all", regex="^(human|system|all)$"),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")

    stmt = (
        select(AuditLog)
        .where(
            AuditLog.entity_type == "document",
            AuditLog.entity_id == document_id,
        )
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    )
    if actor == "human":
        stmt = stmt.where(AuditLog.actor_user_id.is_not(None))
    elif actor == "system":
        stmt = stmt.where(AuditLog.actor_user_id.is_(None))

    rows = db.execute(stmt.limit(limit + 1)).scalars().all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    # Batch-load users.
    user_ids = {r.actor_user_id for r in rows if r.actor_user_id is not None}
    users_by_id: dict[int, User] = {}
    if user_ids:
        users_by_id = {
            u.id: u
            for u in db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
        }

    items: list[dict] = []
    for row in rows:
        is_human = row.actor_user_id is not None
        metadata = row.metadata_ or {}
        if is_human:
            u = users_by_id.get(int(row.actor_user_id))  # type: ignore[arg-type]
            actor_payload: dict = {
                "type": "human",
                "user": {
                    "id": u.id if u else row.actor_user_id,
                    "display_name": u.display_name if u else "(usuario eliminado)",
                },
            }
        else:
            actor_payload = {"type": "system", "user": None}
        items.append(
            {
                "id": row.id,
                "action": row.action,
                "actor": actor_payload,
                "summary": _history_summary(row.action, is_human=is_human, metadata=metadata),
                "metadata": metadata,
                "occurred_at": row.created_at,
            }
        )

    return {"items": items, "next_cursor": None, "has_more": has_more}


# ---------- Serializer ----------


def _can_delete(doc: Document, user: CurrentUser | None) -> bool:
    """Spec 016: ¿este usuario puede intentar borrar este documento?

    Gobierna la visibilidad del botón en el back-office. Deliberadamente NO
    consulta el estado de la celda: hacerlo costaría dos consultas por fila del
    listado. Esa condición se evalúa al ejecutar el borrado, que puede devolver
    409 aunque el campo venga en true.
    """
    if user is None or user.role not in (Role.ADMIN.value, Role.MANAGER.value):
        return False
    if doc.deleted_at is not None or doc.verified:
        return False
    if user.role != Role.ADMIN.value and doc.uploaded_by != user.user_id:
        return False

    grace_hours = get_settings().document_delete_grace_hours
    created_at = doc.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
    return elapsed <= grace_hours * 3600


def _serialize(
    db: Session,
    doc: Document,
    *,
    include_supplier: bool = False,
    user: CurrentUser | None = None,
) -> dict:
    uploader = db.get(User, doc.uploaded_by)
    last_updated_user = db.get(User, doc.last_updated_by) if doc.last_updated_by else None
    verified_user = db.get(User, doc.verified_by) if doc.verified_by else None

    payload: dict = {
        "id": doc.id,
        "supplier_id": doc.supplier_id,
        "document_type_id": doc.document_type_id,
        "coverage_period_start": doc.coverage_period_start,
        "coverage_period_end": doc.coverage_period_end,
        "due_date_calculated": doc.due_date_calculated,
        "due_date_effective": doc.due_date_effective,
        "due_date_override_reason": doc.due_date_override_reason,
        "status": doc.status.value,
        "verified": doc.verified,
        "verified_by": {"id": verified_user.id, "display_name": verified_user.display_name}
        if verified_user
        else None,
        "verified_at": doc.verified_at,
        "verified_note": doc.verified_note,
        "version": doc.version,
        "is_latest": doc.is_latest,
        "can_delete": _can_delete(doc, user),
        "file": {
            "name": doc.file_name_original,
            "size_bytes": doc.file_size_bytes,
            "mime_type": doc.file_mime_type,
            "sha256": doc.file_sha256,
        },
        "ocr": {
            "status": doc.ocr_status.value,
            "extracted_rfc": doc.ocr_extracted_rfc,
            "extracted_issued_at": doc.ocr_extracted_issued_at,
            "extracted_valid_until": doc.ocr_extracted_valid_until,
        },
        "audit": {
            "added": {
                "user": {"id": uploader.id, "display_name": uploader.display_name}
                if uploader
                else None,
                "at": doc.created_at,
            },
            "last_updated": (
                {
                    "user": {
                        "id": last_updated_user.id,
                        "display_name": last_updated_user.display_name,
                    },
                    "at": doc.last_updated_at,
                }
                if last_updated_user and doc.last_updated_at
                else None
            ),
            "validated": (
                {
                    "user": {"id": verified_user.id, "display_name": verified_user.display_name},
                    "at": doc.verified_at,
                    "note": doc.verified_note,
                }
                if verified_user and doc.verified_at
                else None
            ),
        },
        "supplier": None,
    }

    if include_supplier:
        supplier = db.get(Supplier, doc.supplier_id)
        if supplier is not None:
            payload["supplier"] = {"id": supplier.id, "legal_name": supplier.legal_name}

    doc_type = db.get(DocumentType, doc.document_type_id)
    payload["document_type"] = (
        {
            "id": doc_type.id,
            "name": doc_type.name,
            "slug": doc_type.slug,
            "periodicity": doc_type.periodicity.value,
        }
        if doc_type
        else {"id": doc.document_type_id, "name": f"Tipo #{doc.document_type_id}", "slug": "", "periodicity": "none"}
    )

    return payload


# Used elsewhere
_ = Annotated  # quiet linter when imports are minimized later
