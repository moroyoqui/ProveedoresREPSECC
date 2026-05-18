"""DocumentType read-only routes (contracts/document-types.md spec 001)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user
from repse.db.session import get_db
from repse.document_types.models import (
    DocumentType,
    DocumentTypeOrigin,
    DocumentTypeStatus,
    TenantDocumentTypeSetting,
)
from repse.errors import NotFound

router = APIRouter()


@router.get("")
def list_document_types(
    include_inactive: bool = Query(False),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Lists canonical + custom DocumentTypes effective for the tenant.

    Effective activation is computed by joining DocumentType with
    TenantDocumentTypeSetting; canonical types without a setting row are
    considered active by default (FR-007 spec 001).
    """
    # Canonical types (organization_id IS NULL) visible to every tenant.
    # Custom types where organization_id == current tenant (filter auto-applied
    # by TenantOwned would not apply because DocumentType does not inherit it;
    # filter manually).
    types_stmt = (
        select(DocumentType, TenantDocumentTypeSetting)
        .outerjoin(
            TenantDocumentTypeSetting,
            (TenantDocumentTypeSetting.document_type_id == DocumentType.id)
            & (TenantDocumentTypeSetting.organization_id == user.organization_id),
        )
        .where(
            or_(
                DocumentType.organization_id.is_(None),
                DocumentType.organization_id == user.organization_id,
            )
        )
        .order_by(DocumentType.name)
    )
    items = []
    for dt, setting in db.execute(types_stmt).all():
        # Canonical default = active unless setting says otherwise.
        if dt.origin is DocumentTypeOrigin.CANONICAL:
            active = setting.active if setting is not None else True
        else:
            active = dt.status is DocumentTypeStatus.ACTIVE
        if not include_inactive and not active:
            continue
        items.append(
            {
                "id": dt.id,
                "slug": dt.slug,
                "name": dt.name,
                "description": dt.description,
                "periodicity": dt.periodicity.value,
                "origin": dt.origin.value,
                "status": dt.status.value,
                "active": active,
            }
        )
    return {"items": items}


@router.get("/{type_id}")
def get_document_type(
    type_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    dt = db.get(DocumentType, type_id)
    if dt is None:
        raise NotFound("DocumentType not found")
    if dt.origin is DocumentTypeOrigin.CUSTOM and dt.organization_id != user.organization_id:
        raise NotFound("DocumentType not found")
    setting = db.execute(
        select(TenantDocumentTypeSetting).where(
            TenantDocumentTypeSetting.document_type_id == dt.id,
            TenantDocumentTypeSetting.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()
    active = (
        setting.active
        if setting is not None
        else (dt.status is DocumentTypeStatus.ACTIVE)
    )
    return {
        "id": dt.id,
        "slug": dt.slug,
        "name": dt.name,
        "description": dt.description,
        "periodicity": dt.periodicity.value,
        "origin": dt.origin.value,
        "status": dt.status.value,
        "active": active,
    }
