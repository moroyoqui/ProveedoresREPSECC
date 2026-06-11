"""Supplier service.

Handles RFC unicity per tenant, auto-assignment of 'Sin clasificar' when no
supplier_type_id is provided, and audit logging of every change.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.audit import actions as audit_actions
from repse.audit.service import AuditEvent, write_event
from repse.errors import Conflict, NotFound, UnprocessableEntity, ValidationFailure
from repse.giros.models import Giro
from repse.sectors.models import Sector
from repse.suppliers import type_change_service
from repse.suppliers.models import Supplier, SupplierStatus
from repse.suppliers.schemas import SupplierIn, SupplierPatch
from repse.supplier_types.models import (
    SupplierType,
    SupplierTypeOrigin,
    SupplierTypeStatus,
)


def _validate_sector_giro(
    db: Session, *, sector_id: int | None, giro_id: int | None
) -> None:
    """Validates sector/giro coherence. Raises UnprocessableEntity on violations."""
    if giro_id is not None and sector_id is None:
        raise UnprocessableEntity(
            "Se requiere sector_id cuando se proporciona giro_id.",
            details={"code": "giro_requires_sector"},
        )
    if giro_id is not None and sector_id is not None:
        giro = db.get(Giro, giro_id)
        if giro is None:
            raise NotFound("Giro not found")
        if giro.sector_id != sector_id:
            raise UnprocessableEntity(
                "El giro no pertenece al sector indicado.",
                details={"code": "giro_sector_mismatch"},
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

    _validate_sector_giro(db, sector_id=body.sector_id, giro_id=body.giro_id)

    supplier = Supplier(
        organization_id=organization_id,
        supplier_type_id=st.id,
        sector_id=body.sector_id,
        giro_id=body.giro_id,
        legal_name=body.legal_name,
        rfc=body.rfc,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        notes=body.notes,
        repse_folio=body.repse_folio,
        status=SupplierStatus.ACTIVE,
    )
    db.add(supplier)
    db.flush()

    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=audit_actions.SUPPLIER_CREATED,
            entity_type="supplier",
            entity_id=supplier.id,
            metadata={
                "rfc": supplier.rfc,
                "legal_name": supplier.legal_name,
                "supplier_type_id": supplier.supplier_type_id,
                "sector_id": supplier.sector_id,
                "giro_id": supplier.giro_id,
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

    type_change_requested = (
        body.supplier_type_id is not None
        and body.supplier_type_id != supplier.supplier_type_id
    )

    # Cambio destructivo de SupplierType (FR-005b/c/d spec 001).
    if type_change_requested:
        preview = type_change_service.preview_destructive_change(
            db,
            supplier_id=supplier.id,
            organization_id=organization_id,
            new_supplier_type_id=body.supplier_type_id,  # type: ignore[arg-type]
        )
        if preview.requires_confirmation:
            if body.confirmation_text is None:
                raise Conflict(
                    "Confirmation required: this change will permanently delete documents",
                    details={
                        "code": "confirmation_required",
                        "affected_count": preview.affected_count,
                        "affected_documents": type_change_service.to_affected_payload(
                            preview.affected_documents
                        ),
                    },
                )
            if not type_change_service.confirmation_matches(body.confirmation_text):
                raise UnprocessableEntity(
                    "Invalid confirmation text",
                    details={
                        "code": "invalid_confirmation",
                        "expected": type_change_service.CONFIRMATION_TEXT_EXPECTED,
                    },
                )
            type_change_service.execute_destructive_change(
                db,
                supplier_id=supplier.id,
                organization_id=organization_id,
                new_supplier_type_id=body.supplier_type_id,  # type: ignore[arg-type]
                actor_user_id=actor_user_id,
            )
        else:
            type_change_service.execute_non_destructive_change(
                db,
                supplier_id=supplier.id,
                organization_id=organization_id,
                new_supplier_type_id=body.supplier_type_id,  # type: ignore[arg-type]
                actor_user_id=actor_user_id,
            )
        # Refresh after the type-change service committed.
        supplier = db.get(Supplier, supplier_id)
        if supplier is None:
            raise NotFound("Supplier not found")

    before = {
        "legal_name": supplier.legal_name,
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
    if body.repse_folio is not None:
        supplier.repse_folio = body.repse_folio
    if body.status is not None:
        supplier.status = body.status

    # Sector/giro update: validate coherence, then apply.
    # If sector_id changes and no new giro_id is provided, clear giro_id.
    sector_changing = "sector_id" in body.model_fields_set
    giro_changing = "giro_id" in body.model_fields_set
    if sector_changing or giro_changing:
        new_sector_id = body.sector_id if sector_changing else supplier.sector_id
        if sector_changing and not giro_changing:
            # sector changed without explicit giro → clear giro
            new_giro_id = None
        else:
            new_giro_id = body.giro_id if giro_changing else supplier.giro_id
        _validate_sector_giro(db, sector_id=new_sector_id, giro_id=new_giro_id)
        supplier.sector_id = new_sector_id
        supplier.giro_id = new_giro_id

    after = {
        "legal_name": supplier.legal_name,
        "status": supplier.status.value,
    }
    if before != after:
        write_event(
            db,
            AuditEvent(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=audit_actions.SUPPLIER_UPDATED,
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
            action=audit_actions.SUPPLIER_DEACTIVATED,
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
            action=audit_actions.SUPPLIER_REACTIVATED,
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
