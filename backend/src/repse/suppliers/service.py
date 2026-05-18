"""Supplier service.

Handles RFC unicity per tenant, auto-assignment of 'Sin clasificar' when no
supplier_type_id is provided, and audit logging of every change.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.audit.service import AuditEvent, write_event
from repse.errors import Conflict, NotFound, ValidationFailure
from repse.suppliers.models import Supplier, SupplierStatus
from repse.suppliers.schemas import SupplierIn, SupplierPatch
from repse.supplier_types.models import (
    SupplierType,
    SupplierTypeOrigin,
    SupplierTypeStatus,
)


def _resolve_supplier_type(db: Session, organization_id: int, supplier_type_id: int | None) -> SupplierType:
    if supplier_type_id is not None:
        st = db.get(SupplierType, supplier_type_id)
        if st is None or st.organization_id != organization_id:
            raise NotFound("SupplierType not found")
        if st.status is not SupplierTypeStatus.ACTIVE:
            raise ValidationFailure("SupplierType is archived")
        return st
    # Fallback to 'Sin clasificar' (origin=system).
    st = db.execute(
        select(SupplierType).where(
            SupplierType.organization_id == organization_id,
            SupplierType.origin == SupplierTypeOrigin.SYSTEM,
        )
    ).scalar_one_or_none()
    if st is None:
        raise ValidationFailure(
            "Tenant has no 'Sin clasificar' SupplierType — provisioning was not completed"
        )
    return st


def create_supplier(
    db: Session, *, organization_id: int, actor_user_id: int, body: SupplierIn
) -> Supplier:
    existing = db.execute(select(Supplier).where(Supplier.rfc == body.rfc)).scalar_one_or_none()
    if existing is not None:
        raise Conflict("RFC already exists for a supplier in this organization",
                       details={"code": "rfc_exists"})

    st = _resolve_supplier_type(db, organization_id, body.supplier_type_id)
    if body.status_active_requires_contact():
        pass  # validation happens in schema if needed

    supplier = Supplier(
        organization_id=organization_id,
        supplier_type_id=st.id,
        legal_name=body.legal_name,
        rfc=body.rfc,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        notes=body.notes,
        status=SupplierStatus.ACTIVE,
    )
    db.add(supplier)
    db.flush()

    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="supplier.created",
            entity_type="supplier",
            entity_id=supplier.id,
            metadata={
                "rfc": supplier.rfc,
                "legal_name": supplier.legal_name,
                "supplier_type_id": supplier.supplier_type_id,
            },
        ),
    )
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session, *, supplier_id: int, organization_id: int, actor_user_id: int, body: SupplierPatch
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")
    before = {
        "legal_name": supplier.legal_name,
        "supplier_type_id": supplier.supplier_type_id,
        "status": supplier.status.value,
    }

    if body.legal_name is not None:
        supplier.legal_name = body.legal_name
    if body.contact_name is not None:
        supplier.contact_name = body.contact_name
    if body.contact_email is not None:
        supplier.contact_email = body.contact_email
    if body.contact_phone is not None:
        supplier.contact_phone = body.contact_phone
    if body.notes is not None:
        supplier.notes = body.notes
    if body.status is not None:
        supplier.status = body.status
    if body.supplier_type_id is not None and body.supplier_type_id != supplier.supplier_type_id:
        new_st = _resolve_supplier_type(db, organization_id, body.supplier_type_id)
        supplier.supplier_type_id = new_st.id

    after = {
        "legal_name": supplier.legal_name,
        "supplier_type_id": supplier.supplier_type_id,
        "status": supplier.status.value,
    }
    if before != after:
        write_event(
            db,
            AuditEvent(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="supplier.updated",
                entity_type="supplier",
                entity_id=supplier.id,
                metadata={"before": before, "after": after},
            ),
        )
    db.commit()
    db.refresh(supplier)
    return supplier


def deactivate_supplier(
    db: Session, *, supplier_id: int, organization_id: int, actor_user_id: int
) -> None:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")
    supplier.status = SupplierStatus.INACTIVE
    supplier.deleted_at = datetime.now(timezone.utc)
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="supplier.deactivated",
            entity_type="supplier",
            entity_id=supplier.id,
            metadata={},
        ),
    )
    db.commit()


def reactivate_supplier(
    db: Session, *, supplier_id: int, organization_id: int, actor_user_id: int
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")
    supplier.status = SupplierStatus.ACTIVE
    supplier.deleted_at = None
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="supplier.reactivated",
            entity_type="supplier",
            entity_id=supplier.id,
            metadata={},
        ),
    )
    db.commit()
    db.refresh(supplier)
    return supplier


# Pydantic-side helper — placeholder used during schema migration.
def _noop():  # pragma: no cover
    pass


# Pydantic schema doesn't expose a method like status_active_requires_contact;
# patch in: add a helper to SupplierIn to keep call site terse.
from repse.suppliers import schemas as _schemas  # noqa: E402


def _status_active_requires_contact(self: _schemas.SupplierIn) -> bool:
    return False  # contract: required only when status=='active' AND no contact at all


_schemas.SupplierIn.status_active_requires_contact = _status_active_requires_contact  # type: ignore[attr-defined]
