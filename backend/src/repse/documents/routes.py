"""Document routes (contracts/documents.md spec 001)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.config import Settings, get_settings
from repse.db.session import get_db
from repse.documents import service
from repse.documents.models import Document, OcrStatus
from repse.documents.service import UploadInput
from repse.documents.storage import FileStore, InvalidToken, TokenExpired
from repse.errors import Forbidden, NotFound
from repse.users.models import Role, User

router = APIRouter()


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
    return _serialize(db, doc)


@router.get("")
def list_documents(
    supplier_id: int | None = None,
    document_type_id: int | None = None,
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
    if is_latest:
        stmt = stmt.where(Document.is_latest.is_(True))
    docs = db.execute(stmt.limit(limit + 1)).scalars().all()
    has_more = len(docs) > limit
    docs = docs[:limit]
    return {
        "items": [_serialize(db, d) for d in docs],
        "next_cursor": None,
        "has_more": has_more,
    }


@router.get("/{document_id}")
def get_document(
    document_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")
    return _serialize(db, doc)


# ---------- Download tokens + serving ----------


@router.post("/{document_id}/download-token")
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


@router.get("/files/{token}", include_in_schema=False)
def download_file(
    token: str,
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
    if doc is None or doc.organization_id != user.organization_id:
        raise NotFound("Document not found")

    fh = store.open(doc.file_path)
    return StreamingResponse(
        fh,
        media_type=doc.file_mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name_original}"'},
    )


# ---------- Verify / unverify ----------


@router.post("/{document_id}/verify")
def verify_document_route(
    document_id: int,
    body: dict,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> dict:
    doc = service.verify_document(
        db,
        document_id=document_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        note=body.get("note"),
    )
    return _serialize(db, doc)


@router.post("/{document_id}/unverify")
def unverify_document_route(
    document_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    doc = service.unverify_document(
        db,
        document_id=document_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return _serialize(db, doc)


# ---------- Serializer ----------


def _serialize(db: Session, doc: Document) -> dict:
    uploader = db.get(User, doc.uploaded_by)
    last_updated_user = db.get(User, doc.last_updated_by) if doc.last_updated_by else None
    verified_user = db.get(User, doc.verified_by) if doc.verified_by else None

    return {
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
    }


# Used elsewhere
_ = Annotated  # quiet linter when imports are minimized later
