"""SupplierType + requirements service (spec 003).

Rules enforced here (data-model.md + research.md):
  * 'Sin clasificar' (origin=system) is immutable: no update, archive, delete.
  * Name unique per tenant, case-insensitive.
  * Cannot delete a tenant-custom type that still has suppliers OR requirements
    attached — caller should archive instead.
  * Adding a requirement against an inactive (archived/deactivated) DocumentType
    is rejected with `doc_type_inactive`.
  * Every mutation writes an audit_log entry.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.audit.service import AuditEvent, write_event
from repse.document_types.models import (
    DocumentType,
    DocumentTypeOrigin,
    DocumentTypeStatus,
    Periodicity,
    TenantDocumentTypeSetting,
)
from repse.errors import Conflict, Forbidden, NotFound, ValidationFailure
from repse.suppliers.models import Supplier
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierType,
    SupplierTypeDocumentRequirement,
    SupplierTypeOrigin,
    SupplierTypeStatus,
)


# ---------- helpers ----------


def _normalize(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def _ensure_name_unique(
    db: Session, *, organization_id: int, name: str, exclude_id: int | None = None
) -> None:
    candidate = _normalize(name)
    rows = db.execute(select(SupplierType).where(SupplierType.organization_id == organization_id)).scalars().all()
    for r in rows:
        if exclude_id is not None and r.id == exclude_id:
            continue
        if _normalize(r.name) == candidate:
            raise Conflict("Name already exists for this tenant", details={"code": "name_exists"})


def _guard_not_system(supplier_type: SupplierType, action: str) -> None:
    if supplier_type.origin is SupplierTypeOrigin.SYSTEM:
        raise Forbidden(
            f"Cannot {action} the 'Sin clasificar' SupplierType",
            details={"code": "system_type_immutable"},
        )


def _audit(
    db: Session,
    *,
    organization_id: int,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    metadata: dict[str, Any],
) -> None:
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        ),
    )


# ---------- SupplierType CRUD ----------


def create_supplier_type(
    db: Session, *, organization_id: int, actor_user_id: int, name: str, description: str | None
) -> SupplierType:
    _ensure_name_unique(db, organization_id=organization_id, name=name)
    row = SupplierType(
        organization_id=organization_id,
        name=name.strip(),
        description=description,
        origin=SupplierTypeOrigin.CUSTOM,
        status=SupplierTypeStatus.ACTIVE,
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="supplier_type.created",
        entity_type="supplier_type",
        entity_id=row.id,
        metadata={"name": row.name},
    )
    db.commit()
    db.refresh(row)
    return row


def update_supplier_type(
    db: Session,
    *,
    supplier_type_id: int,
    organization_id: int,
    actor_user_id: int,
    name: str | None,
    description: str | None,
) -> SupplierType:
    row = db.get(SupplierType, supplier_type_id)
    if row is None:
        raise NotFound("SupplierType not found")
    _guard_not_system(row, "update")

    before = {"name": row.name, "description": row.description}
    if name is not None and name.strip() != row.name:
        _ensure_name_unique(db, organization_id=organization_id, name=name, exclude_id=row.id)
        row.name = name.strip()
    if description is not None:
        row.description = description

    after = {"name": row.name, "description": row.description}
    if before != after:
        _audit(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="supplier_type.updated",
            entity_type="supplier_type",
            entity_id=row.id,
            metadata={"before": before, "after": after},
        )
    db.commit()
    db.refresh(row)
    return row


def archive_supplier_type(
    db: Session, *, supplier_type_id: int, organization_id: int, actor_user_id: int, reason: str | None
) -> tuple[SupplierType, int]:
    row = db.get(SupplierType, supplier_type_id)
    if row is None:
        raise NotFound("SupplierType not found")
    _guard_not_system(row, "archive")
    if row.status is SupplierTypeStatus.ARCHIVED:
        raise Conflict("Already archived", details={"code": "already_archived"})

    affected = db.execute(
        select(func.count()).select_from(Supplier).where(Supplier.supplier_type_id == row.id)
    ).scalar_one()
    row.status = SupplierTypeStatus.ARCHIVED
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="supplier_type.archived",
        entity_type="supplier_type",
        entity_id=row.id,
        metadata={"reason": reason or "", "affected_suppliers_count": affected},
    )
    db.commit()
    db.refresh(row)
    return row, affected


def restore_supplier_type(
    db: Session, *, supplier_type_id: int, organization_id: int, actor_user_id: int
) -> SupplierType:
    row = db.get(SupplierType, supplier_type_id)
    if row is None:
        raise NotFound("SupplierType not found")
    if row.status is SupplierTypeStatus.ACTIVE:
        return row
    row.status = SupplierTypeStatus.ACTIVE
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="supplier_type.restored",
        entity_type="supplier_type",
        entity_id=row.id,
        metadata={},
    )
    db.commit()
    db.refresh(row)
    return row


def delete_supplier_type(
    db: Session, *, supplier_type_id: int, organization_id: int, actor_user_id: int
) -> None:
    row = db.get(SupplierType, supplier_type_id)
    if row is None:
        raise NotFound("SupplierType not found")
    _guard_not_system(row, "delete")

    sup_cnt = db.execute(
        select(func.count()).select_from(Supplier).where(Supplier.supplier_type_id == row.id)
    ).scalar_one()
    req_cnt = db.execute(
        select(func.count())
        .select_from(SupplierTypeDocumentRequirement)
        .where(SupplierTypeDocumentRequirement.supplier_type_id == row.id)
    ).scalar_one()
    if sup_cnt > 0 or req_cnt > 0:
        raise Conflict(
            "Cannot delete a SupplierType that has suppliers or requirements; archive it instead",
            details={
                "code": "has_dependencies",
                "supplier_count": int(sup_cnt),
                "requirement_count": int(req_cnt),
            },
        )

    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="supplier_type.deleted",
        entity_type="supplier_type",
        entity_id=row.id,
        metadata={"name": row.name},
    )
    db.delete(row)
    db.commit()


# ---------- Requirements CRUD ----------


def _resolve_doc_type_for_tenant(db: Session, organization_id: int, doc_type_id: int) -> DocumentType:
    dt = db.get(DocumentType, doc_type_id)
    if dt is None:
        raise NotFound("DocumentType not found")
    if dt.origin is DocumentTypeOrigin.CUSTOM and dt.organization_id != organization_id:
        raise NotFound("DocumentType not found")
    if dt.status is DocumentTypeStatus.ARCHIVED:
        raise Conflict(
            "DocumentType is archived; reactivate it before associating",
            details={"code": "doc_type_inactive"},
        )
    if dt.origin is DocumentTypeOrigin.CANONICAL:
        setting = db.execute(
            select(TenantDocumentTypeSetting).where(
                TenantDocumentTypeSetting.organization_id == organization_id,
                TenantDocumentTypeSetting.document_type_id == dt.id,
            )
        ).scalar_one_or_none()
        if setting is not None and not setting.active:
            raise Conflict(
                "DocumentType is deactivated in this tenant; reactivate before associating",
                details={"code": "doc_type_inactive"},
            )
    return dt


def create_requirement(
    db: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    supplier_type_id: int,
    document_type_id: int,
    periodicity_override: Periodicity | None,
) -> SupplierTypeDocumentRequirement:
    st = db.get(SupplierType, supplier_type_id)
    if st is None:
        raise NotFound("SupplierType not found")
    dt = _resolve_doc_type_for_tenant(db, organization_id, document_type_id)

    existing = db.execute(
        select(SupplierTypeDocumentRequirement).where(
            SupplierTypeDocumentRequirement.supplier_type_id == st.id,
            SupplierTypeDocumentRequirement.document_type_id == dt.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status is RequirementStatus.ACTIVE:
            raise Conflict(
                "Requirement already exists",
                details={"code": "already_exists", "requirement_id": existing.id},
            )
        existing.status = RequirementStatus.ACTIVE
        existing.periodicity_override = periodicity_override
        _audit(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="requirement.restored",
            entity_type="supplier_type_requirement",
            entity_id=existing.id,
            metadata={"document_type_id": dt.id, "periodicity_override": (
                periodicity_override.value if periodicity_override else None
            )},
        )
        db.commit()
        db.refresh(existing)
        return existing

    req = SupplierTypeDocumentRequirement(
        organization_id=organization_id,
        supplier_type_id=st.id,
        document_type_id=dt.id,
        periodicity_override=periodicity_override,
        status=RequirementStatus.ACTIVE,
        created_by=actor_user_id,
    )
    db.add(req)
    db.flush()
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="requirement.created",
        entity_type="supplier_type_requirement",
        entity_id=req.id,
        metadata={
            "supplier_type_id": st.id,
            "document_type_id": dt.id,
            "periodicity_override": periodicity_override.value if periodicity_override else None,
        },
    )
    db.commit()
    db.refresh(req)
    return req


def update_requirement_periodicity(
    db: Session,
    *,
    requirement_id: int,
    organization_id: int,
    actor_user_id: int,
    periodicity_override: Periodicity | None,
) -> SupplierTypeDocumentRequirement:
    row = db.get(SupplierTypeDocumentRequirement, requirement_id)
    if row is None:
        raise NotFound("Requirement not found")
    prev = row.periodicity_override
    if prev == periodicity_override:
        return row
    row.periodicity_override = periodicity_override
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="requirement.periodicity_changed",
        entity_type="supplier_type_requirement",
        entity_id=row.id,
        metadata={
            "prev": prev.value if prev else None,
            "new": periodicity_override.value if periodicity_override else None,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def retire_requirement(
    db: Session, *, requirement_id: int, organization_id: int, actor_user_id: int
) -> None:
    row = db.get(SupplierTypeDocumentRequirement, requirement_id)
    if row is None:
        raise NotFound("Requirement not found")
    row.status = RequirementStatus.RETIRED
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="requirement.retired",
        entity_type="supplier_type_requirement",
        entity_id=row.id,
        metadata={},
    )
    db.commit()
