"""SupplierType read-only routes (contracts/supplier-types.md spec 001).

Write endpoints (POST/PATCH/DELETE/archive/restore + requirements + templates)
belong to spec 003 and are NOT implemented here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import current_user
from repse.db.session import get_db
from repse.document_types.models import DocumentType
from repse.errors import NotFound
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
            }
        )
    return out
