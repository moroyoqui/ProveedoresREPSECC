"""SupplierType routes — read + admin write (spec 003)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.common.if_match import assert_fresh, require_if_match
from repse.db.session import get_db
from repse.document_types.models import DocumentType
from repse.errors import NotFound
from repse.supplier_types import service
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierType,
    SupplierTypeDocumentRequirement,
    SupplierTypeStatus,
)

router = APIRouter()


def _counts(db: Session, st: SupplierType) -> tuple[int, int]:
    from repse.suppliers.models import Supplier  # local import

    supplier_count = db.execute(
        select(func.count())
        .select_from(Supplier)
        .where(Supplier.supplier_type_id == st.id)
    ).scalar_one()
    requirement_count = db.execute(
        select(func.count())
        .select_from(SupplierTypeDocumentRequirement)
        .where(
            SupplierTypeDocumentRequirement.supplier_type_id == st.id,
            SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
        )
    ).scalar_one()
    return supplier_count, requirement_count


@router.get("")
def list_supplier_types(
    status: str = Query("active"),
    include_requirements: bool = Query(False),
    _user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(SupplierType).order_by(SupplierType.name)
    if status != "all":
        stmt = stmt.where(SupplierType.status == SupplierTypeStatus(status))
    types = db.execute(stmt).scalars().all()
    items = []
    for st in types:
        sc, rc = _counts(db, st)
        item = {
            "id": st.id,
            "name": st.name,
            "description": st.description,
            "origin": st.origin.value,
            "status": st.status.value,
            "supplier_count": sc,
            "requirement_count": rc,
            "updated_at": st.updated_at.isoformat() if st.updated_at else None,
        }
        if include_requirements:
            item["requirements"] = _serialize_requirements(db, st)
        items.append(item)
    return {"items": items}


@router.get("/{type_id}")
def get_supplier_type(
    type_id: int,
    _user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    st = db.get(SupplierType, type_id)
    if st is None:
        raise NotFound("SupplierType not found")
    sc, rc = _counts(db, st)
    return {
        "id": st.id,
        "name": st.name,
        "description": st.description,
        "origin": st.origin.value,
        "status": st.status.value,
        "supplier_count": sc,
        "requirement_count": rc,
        "updated_at": st.updated_at.isoformat() if st.updated_at else None,
        "requirements": _serialize_requirements(db, st),
    }


def _serialize_requirements(db: Session, st: SupplierType) -> list[dict]:
    rows = (
        db.execute(
            select(SupplierTypeDocumentRequirement, DocumentType)
            .join(DocumentType, DocumentType.id == SupplierTypeDocumentRequirement.document_type_id)
            .where(SupplierTypeDocumentRequirement.supplier_type_id == st.id)
            .order_by(DocumentType.name)
        ).all()
    )
    out = []
    for req, dt in rows:
        out.append(
            {
                "id": req.id,
                "document_type": {
                    "id": dt.id,
                    "slug": dt.slug,
                    "name": dt.name,
                    "periodicity": dt.periodicity.value,
                    "origin": dt.origin.value,
                    "status": dt.status.value,
                },
                "periodicity_override": req.periodicity_override.value
                if req.periodicity_override
                else None,
                "periodicity_effective": (req.periodicity_override or dt.periodicity).value,
                "status": req.status.value,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Write endpoints (spec 003 admin)
# ---------------------------------------------------------------------------


from repse.supplier_types.schemas import (  # noqa: E402
    ArchiveIn,
    RequirementCreate,
    RequirementPatch,
    SupplierTypeCreate,
    SupplierTypePatch,
)
from repse.users.models import Role  # noqa: E402


def _serialize_one(db: Session, st: SupplierType) -> dict:
    sc, rc = _counts(db, st)
    return {
        "id": st.id,
        "name": st.name,
        "description": st.description,
        "origin": st.origin.value,
        "status": st.status.value,
        "supplier_count": sc,
        "requirement_count": rc,
        "updated_at": st.updated_at.isoformat() if st.updated_at else None,
    }


@router.post("", status_code=201)
def create_supplier_type_route(
    body: SupplierTypeCreate,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    row = service.create_supplier_type(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        name=body.name,
        description=body.description,
    )
    return _serialize_one(db, row)


@router.patch("/{type_id}")
def update_supplier_type_route(
    type_id: int,
    body: SupplierTypePatch,
    expected_updated_at=Depends(require_if_match),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    st = db.get(SupplierType, type_id)
    if st is None:
        raise NotFound("SupplierType not found")
    assert_fresh(expected_updated_at, st.updated_at, current_payload=_serialize_one(db, st))
    row = service.update_supplier_type(
        db,
        supplier_type_id=type_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        name=body.name,
        description=body.description,
    )
    return _serialize_one(db, row)


@router.post("/{type_id}/archive")
def archive_supplier_type_route(
    type_id: int,
    body: ArchiveIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    row, affected = service.archive_supplier_type(
        db,
        supplier_type_id=type_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        reason=body.reason,
    )
    out = _serialize_one(db, row)
    out["affected_suppliers_count"] = affected
    return out


@router.post("/{type_id}/restore")
def restore_supplier_type_route(
    type_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    row = service.restore_supplier_type(
        db,
        supplier_type_id=type_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return _serialize_one(db, row)


@router.delete("/{type_id}", status_code=204)
def delete_supplier_type_route(
    type_id: int,
    expected_updated_at=Depends(require_if_match),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Response:
    st = db.get(SupplierType, type_id)
    if st is None:
        raise NotFound("SupplierType not found")
    assert_fresh(expected_updated_at, st.updated_at, current_payload=_serialize_one(db, st))
    service.delete_supplier_type(
        db,
        supplier_type_id=type_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return Response(status_code=204)


# ---------- Requirements ----------


@router.get("/{type_id}/requirements")
def list_requirements_route(
    type_id: int,
    _user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    st = db.get(SupplierType, type_id)
    if st is None:
        raise NotFound("SupplierType not found")
    return {"items": _serialize_requirements(db, st)}


@router.post("/{type_id}/requirements", status_code=201)
def create_requirement_route(
    type_id: int,
    body: RequirementCreate,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    req = service.create_requirement(
        db,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        supplier_type_id=type_id,
        document_type_id=body.document_type_id,
        periodicity_override=body.periodicity_override,
    )
    dt = db.get(DocumentType, req.document_type_id)
    return {
        "id": req.id,
        "document_type": {
            "id": dt.id, "slug": dt.slug, "name": dt.name, "periodicity": dt.periodicity.value,
            "origin": dt.origin.value, "status": dt.status.value,
        },
        "periodicity_override": req.periodicity_override.value if req.periodicity_override else None,
        "periodicity_effective": (req.periodicity_override or dt.periodicity).value,
        "status": req.status.value,
        "created_at": req.created_at.isoformat(),
        "updated_at": req.updated_at.isoformat(),
    }


# Separate router for /supplier-type-requirements/{req_id} top-level paths.
requirements_router = APIRouter()


@requirements_router.patch("/{req_id}")
def patch_requirement_route(
    req_id: int,
    body: RequirementPatch,
    expected_updated_at=Depends(require_if_match),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(SupplierTypeDocumentRequirement, req_id)
    if row is None:
        raise NotFound("Requirement not found")
    assert_fresh(expected_updated_at, row.updated_at)
    row = service.update_requirement_periodicity(
        db,
        requirement_id=req_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        periodicity_override=body.periodicity_override,
    )
    dt = db.get(DocumentType, row.document_type_id)
    return {
        "id": row.id,
        "document_type": {
            "id": dt.id, "slug": dt.slug, "name": dt.name, "periodicity": dt.periodicity.value,
            "origin": dt.origin.value, "status": dt.status.value,
        },
        "periodicity_override": row.periodicity_override.value if row.periodicity_override else None,
        "periodicity_effective": (row.periodicity_override or dt.periodicity).value,
        "status": row.status.value,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@requirements_router.delete("/{req_id}", status_code=204)
def delete_requirement_route(
    req_id: int,
    expected_updated_at=Depends(require_if_match),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Response:
    row = db.get(SupplierTypeDocumentRequirement, req_id)
    if row is None:
        raise NotFound("Requirement not found")
    assert_fresh(expected_updated_at, row.updated_at)
    service.retire_requirement(
        db,
        requirement_id=req_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return Response(status_code=204)
