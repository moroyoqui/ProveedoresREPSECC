"""DocumentType routes (contracts/document-types.md spec 001 + spec 003 admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.common.if_match import assert_fresh, require_if_match
from repse.db.session import get_db
from repse.document_types import service
from repse.document_types.models import (
    DocumentType,
    DocumentTypeOrigin,
    DocumentTypeStatus,
    TenantDocumentTypeSetting,
)
from repse.document_types.schemas import (
    CanonicalToggle,
    DocumentTypeCreate,
    DocumentTypePatch,
)
from repse.errors import NotFound
from repse.users.models import Role

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
                "updated_at": dt.updated_at.isoformat() if dt.updated_at else None,
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
        "updated_at": dt.updated_at.isoformat() if dt.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Write endpoints (spec 003 admin)
# ---------------------------------------------------------------------------


def _serialize_dt(db: Session, dt: DocumentType, organization_id: int) -> dict:
    setting = db.execute(
        select(TenantDocumentTypeSetting).where(
            TenantDocumentTypeSetting.document_type_id == dt.id,
            TenantDocumentTypeSetting.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if dt.origin is DocumentTypeOrigin.CANONICAL:
        active = setting.active if setting is not None else True
    else:
        active = dt.status is DocumentTypeStatus.ACTIVE
    return {
        "id": dt.id,
        "slug": dt.slug,
        "name": dt.name,
        "description": dt.description,
        "periodicity": dt.periodicity.value,
        "origin": dt.origin.value,
        "status": dt.status.value,
        "active": active,
        "updated_at": dt.updated_at.isoformat() if dt.updated_at else None,
    }


@router.post("", status_code=201)
def create_custom_route(
    body: DocumentTypeCreate,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    dt = service.create_custom(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        name=body.name,
        periodicity=body.periodicity,
        description=body.description,
    )
    return _serialize_dt(db, dt, user.organization_id)


@router.patch("/{type_id}")
def update_custom_route(
    type_id: int,
    body: DocumentTypePatch,
    expected_updated_at=Depends(require_if_match),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    dt = db.get(DocumentType, type_id)
    if dt is None:
        raise NotFound("DocumentType not found")
    assert_fresh(expected_updated_at, dt.updated_at)
    dt = service.update_custom(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        document_type_id=type_id,
        name=body.name,
        description=body.description,
        periodicity=body.periodicity,
    )
    return _serialize_dt(db, dt, user.organization_id)


@router.post("/{type_id}/toggle-active")
def toggle_canonical_route(
    type_id: int,
    body: CanonicalToggle,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    """Activate/deactivate a canonical DocumentType within the current tenant."""
    return service.set_canonical_active(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        document_type_id=type_id,
        active=body.active,
        reason=body.reason,
    )


@router.post("/{type_id}/archive")
def archive_custom_route(
    type_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    dt = service.archive_custom(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        document_type_id=type_id,
    )
    return _serialize_dt(db, dt, user.organization_id)


@router.post("/{type_id}/restore")
def restore_custom_route(
    type_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    dt = service.restore_custom(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        document_type_id=type_id,
    )
    return _serialize_dt(db, dt, user.organization_id)


@router.delete("/{type_id}", status_code=204)
def delete_custom_route(
    type_id: int,
    expected_updated_at=Depends(require_if_match),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Response:
    dt = db.get(DocumentType, type_id)
    if dt is None:
        raise NotFound("DocumentType not found")
    assert_fresh(expected_updated_at, dt.updated_at)
    service.delete_custom(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        document_type_id=type_id,
    )
    return Response(status_code=204)
