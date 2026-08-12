"""Supplier routes (contracts/suppliers.md spec 001)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.db.session import get_db
from repse.document_types.models import DocumentType
from repse.documents.models import Document
from repse.errors import NotFound
from repse.suppliers import compliance as compliance_service
from repse.suppliers import service, type_change_service
from repse.suppliers.models import Supplier, SupplierStatus
from repse.suppliers.schemas import (
    AffectedDocumentOut,
    SupplierDetailOut,
    SupplierIn,
    SupplierListItem,
    SupplierListPage,
    SupplierPatch,
    SupplierTypeChangePreviewOut,
)
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierType,
    SupplierTypeDocumentRequirement,
)
from repse.users.models import Role

router = APIRouter()


@router.get("", response_model=SupplierListPage)
def list_suppliers(
    q: str | None = Query(None),
    status: str = Query("active"),
    supplier_type_id: list[int] | None = Query(None),
    sector_id: int | None = Query(None),
    giro_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> SupplierListPage:
    stmt = select(Supplier).order_by(Supplier.legal_name)
    if status != "all":
        stmt = stmt.where(Supplier.status == SupplierStatus(status))
    if q:
        pat = f"%{q}%"
        stmt = stmt.where(or_(Supplier.legal_name.ilike(pat), Supplier.rfc.ilike(pat)))
    if supplier_type_id:
        stmt = stmt.where(Supplier.supplier_type_id.in_(supplier_type_id))
    if sector_id is not None:
        stmt = stmt.where(Supplier.sector_id == sector_id)
    if giro_id is not None:
        stmt = stmt.where(Supplier.giro_id == giro_id)
    suppliers = db.execute(stmt.limit(limit + 1)).scalars().all()
    has_more = len(suppliers) > limit
    suppliers = suppliers[:limit]

    items = [_serialize_list_item(db, s) for s in suppliers]
    return SupplierListPage(items=items, next_cursor=None, has_more=has_more)


@router.post("", response_model=SupplierListItem, status_code=201)
def create_supplier_route(
    body: SupplierIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> SupplierListItem:
    supplier = service.create_supplier(
        db, organization_id=user.organization_id, actor_user_id=user.user_id, body=body
    )
    return _serialize_list_item(db, supplier)


@router.get("/{supplier_id}", response_model=SupplierDetailOut)
def get_supplier(
    supplier_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> SupplierDetailOut:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")
    return _serialize_detail(db, supplier)


@router.get(
    "/{supplier_id}/type-change-preview",
    response_model=SupplierTypeChangePreviewOut,
)
def preview_type_change(
    supplier_id: int,
    supplier_type_id: int = Query(..., ge=1),
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> SupplierTypeChangePreviewOut:
    preview = type_change_service.preview_destructive_change(
        db,
        supplier_id=supplier_id,
        organization_id=user.organization_id,
        new_supplier_type_id=supplier_type_id,
    )
    payload = type_change_service.to_affected_payload(preview.affected_documents)
    return SupplierTypeChangePreviewOut(
        requires_confirmation=preview.requires_confirmation,
        affected_count=preview.affected_count,
        affected_documents=[AffectedDocumentOut(**item) for item in payload],
    )


@router.patch("/{supplier_id}", response_model=SupplierDetailOut)
def update_supplier_route(
    supplier_id: int,
    body: SupplierPatch,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> SupplierDetailOut:
    supplier = service.update_supplier(
        db,
        supplier_id=supplier_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        body=body,
    )
    return _serialize_detail(db, supplier)


@router.delete("/{supplier_id}", status_code=204)
def deactivate_supplier_route(
    supplier_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Response:
    service.deactivate_supplier(
        db,
        supplier_id=supplier_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return Response(status_code=204)


@router.post("/{supplier_id}/reactivate", response_model=SupplierDetailOut)
def reactivate_supplier_route(
    supplier_id: int,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> SupplierDetailOut:
    supplier = service.reactivate_supplier(
        db,
        supplier_id=supplier_id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return _serialize_detail(db, supplier)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _counts_for(db: Session, supplier: Supplier) -> tuple[dict, int]:
    """Returns ({valid, expiring_soon, expired, missing}, compliance_percent).

    Delegado a ``suppliers.compliance.aggregate`` (T094 spec 001) para que la
    derivación de "missing" desde ``SupplierType.requirements`` (FR-012b) viva
    en un único lugar.
    """
    agg = compliance_service.aggregate(db, supplier_id=supplier.id)
    return dict(agg["counts"]), agg["percent"]


def _sector_dict(supplier: Supplier) -> dict | None:
    if supplier.sector_id is None or supplier.sector is None:
        return None
    return {"id": supplier.sector.id, "name": supplier.sector.name}


def _giro_dict(supplier: Supplier) -> dict | None:
    if supplier.giro_id is None or supplier.giro is None:
        return None
    return {"id": supplier.giro.id, "name": supplier.giro.name}


def _serialize_list_item(db: Session, supplier: Supplier) -> SupplierListItem:
    st = db.get(SupplierType, supplier.supplier_type_id)
    counts, pct = _counts_for(db, supplier)
    return SupplierListItem(
        id=supplier.id,
        legal_name=supplier.legal_name,
        rfc=supplier.rfc,
        supplier_type={"id": st.id, "name": st.name, "origin": st.origin.value} if st else {},
        sector=_sector_dict(supplier),
        giro=_giro_dict(supplier),
        contact_name=supplier.contact_name,
        contact_email=supplier.contact_email,
        status=supplier.status,
        compliance_percent=pct,
        counts=counts,
        created_at=supplier.created_at,
    )


def _serialize_detail(db: Session, supplier: Supplier) -> SupplierDetailOut:
    st = db.get(SupplierType, supplier.supplier_type_id)
    counts, pct = _counts_for(db, supplier)

    requirements = db.execute(
        select(SupplierTypeDocumentRequirement, DocumentType)
        .join(DocumentType, DocumentType.id == SupplierTypeDocumentRequirement.document_type_id)
        .where(
            SupplierTypeDocumentRequirement.supplier_type_id == supplier.supplier_type_id,
            SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
        )
        .order_by(DocumentType.name)
    ).all()

    docs_by_type: list[dict] = []
    for req, dt in requirements:
        latest = db.execute(
            select(Document).where(
                Document.supplier_id == supplier.id,
                Document.document_type_id == dt.id,
                Document.is_latest.is_(True),
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        item: dict = {
            "document_type": {
                "id": dt.id,
                "slug": dt.slug,
                "name": dt.name,
                "periodicity": dt.periodicity.value,
            },
            "latest": None,
            "status_override": None,
        }
        if latest is None:
            item["status_override"] = "missing"
        else:
            item["latest"] = {
                "id": latest.id,
                "coverage_period_start": latest.coverage_period_start,
                "coverage_period_end": latest.coverage_period_end,
                "due_date_effective": latest.due_date_effective,
                "status": latest.status.value,
                "verified": latest.verified,
                "uploaded_at": latest.created_at,
            }
        docs_by_type.append(item)

    return SupplierDetailOut(
        id=supplier.id,
        legal_name=supplier.legal_name,
        rfc=supplier.rfc,
        supplier_type={"id": st.id, "name": st.name, "origin": st.origin.value} if st else {},
        sector=_sector_dict(supplier),
        giro=_giro_dict(supplier),
        contact_name=supplier.contact_name,
        contact_email=supplier.contact_email,
        contact_phone=supplier.contact_phone,
        repse_folio=supplier.repse_folio,
        status=supplier.status,
        compliance_percent=pct,
        counts=counts,
        documents_by_type=docs_by_type,
        created_at=supplier.created_at,
    )
