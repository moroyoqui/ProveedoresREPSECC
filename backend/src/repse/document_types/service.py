"""DocumentType admin service (spec 003).

Handles activation/deactivation of canonical types per tenant (via
`TenantDocumentTypeSetting`) and CRUD of tenant-custom types.

Rules:
  * Canonical DocumentTypes (organization_id IS NULL) are never modified
    directly; activation lives in `tenant_document_type_settings`.
  * Custom DocumentTypes belong to a tenant. Name unique per tenant
    (canonical names + custom names sharing one namespace).
  * Cannot delete a custom DocumentType that has documents or active
    requirements; the caller should archive instead.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from repse.audit.service import AuditEvent, write_event
from repse.document_types.models import (
    DocumentType,
    DocumentTypeOrigin,
    DocumentTypeStatus,
    Periodicity,
    TenantDocumentTypeSetting,
)
from repse.documents.models import Document
from repse.errors import Conflict, Forbidden, NotFound
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierTypeDocumentRequirement,
)


def _normalize(name: str) -> str:
    return " ".join(name.strip().split()).lower()


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


def _ensure_name_unique(
    db: Session, *, organization_id: int, name: str, exclude_id: int | None = None
) -> None:
    candidate = _normalize(name)
    rows = db.execute(
        select(DocumentType).where(
            or_(DocumentType.organization_id.is_(None), DocumentType.organization_id == organization_id),
        )
    ).scalars().all()
    for r in rows:
        if exclude_id is not None and r.id == exclude_id:
            continue
        if _normalize(r.name) == candidate:
            raise Conflict(
                "DocumentType name already exists in this tenant",
                details={"code": "name_exists"},
            )


# ---------- Activate/deactivate canonical (US1 spec 003) ----------


def set_canonical_active(
    db: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    document_type_id: int,
    active: bool,
    reason: str | None = None,
) -> dict:
    dt = db.get(DocumentType, document_type_id)
    if dt is None:
        raise NotFound("DocumentType not found")
    if dt.origin is not DocumentTypeOrigin.CANONICAL:
        raise Forbidden(
            "Only canonical DocumentTypes use the activation toggle",
            details={"code": "canonical_only"},
        )

    setting = db.execute(
        select(TenantDocumentTypeSetting).where(
            TenantDocumentTypeSetting.organization_id == organization_id,
            TenantDocumentTypeSetting.document_type_id == dt.id,
        )
    ).scalar_one_or_none()
    prev_active = setting.active if setting is not None else True

    now = datetime.now(timezone.utc)
    if setting is None:
        setting = TenantDocumentTypeSetting(
            organization_id=organization_id,
            document_type_id=dt.id,
            active=active,
            last_changed_by=actor_user_id,
            last_changed_at=now,
        )
        db.add(setting)
    else:
        setting.active = active
        setting.last_changed_by = actor_user_id
        setting.last_changed_at = now

    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=("document_type.activated_canonical" if active else "document_type.deactivated_canonical"),
        entity_type="document_type",
        entity_id=dt.id,
        metadata={"prev_active": prev_active, "active": active, "reason": reason or ""},
    )
    db.commit()
    return {"id": dt.id, "slug": dt.slug, "name": dt.name, "active": active}


# ---------- Custom DocumentType CRUD (US2 spec 003) ----------


def create_custom(
    db: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    name: str,
    periodicity: Periodicity,
    description: str | None,
) -> DocumentType:
    _ensure_name_unique(db, organization_id=organization_id, name=name)

    # Generate a slug from name; ensure unique by appending the tenant id.
    base_slug = _slugify(name)
    slug = f"{base_slug}-org{organization_id}"
    # If by some chance the slug already exists, append a counter.
    existing = db.execute(select(DocumentType).where(DocumentType.slug == slug)).scalar_one_or_none()
    i = 2
    while existing is not None:
        slug = f"{base_slug}-org{organization_id}-{i}"
        existing = db.execute(select(DocumentType).where(DocumentType.slug == slug)).scalar_one_or_none()
        i += 1

    dt = DocumentType(
        slug=slug,
        name=name.strip(),
        description=description,
        periodicity=periodicity,
        origin=DocumentTypeOrigin.CUSTOM,
        organization_id=organization_id,
        status=DocumentTypeStatus.ACTIVE,
    )
    db.add(dt)
    db.flush()
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="document_type.created",
        entity_type="document_type",
        entity_id=dt.id,
        metadata={"name": dt.name, "periodicity": periodicity.value},
    )
    db.commit()
    db.refresh(dt)
    return dt


def update_custom(
    db: Session,
    *,
    organization_id: int,
    actor_user_id: int,
    document_type_id: int,
    name: str | None,
    description: str | None,
    periodicity: Periodicity | None,
) -> DocumentType:
    dt = db.get(DocumentType, document_type_id)
    if dt is None or (dt.origin is DocumentTypeOrigin.CUSTOM and dt.organization_id != organization_id):
        raise NotFound("DocumentType not found")
    if dt.origin is DocumentTypeOrigin.CANONICAL:
        raise Forbidden(
            "Canonical DocumentTypes cannot be edited",
            details={"code": "canonical_type_immutable"},
        )

    before = {"name": dt.name, "description": dt.description, "periodicity": dt.periodicity.value}
    if name is not None and name.strip() != dt.name:
        _ensure_name_unique(db, organization_id=organization_id, name=name, exclude_id=dt.id)
        dt.name = name.strip()
    if description is not None:
        dt.description = description
    if periodicity is not None:
        dt.periodicity = periodicity
    after = {"name": dt.name, "description": dt.description, "periodicity": dt.periodicity.value}

    if before != after:
        _audit(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="document_type.updated",
            entity_type="document_type",
            entity_id=dt.id,
            metadata={"before": before, "after": after},
        )
    db.commit()
    db.refresh(dt)
    return dt


def archive_custom(
    db: Session, *, organization_id: int, actor_user_id: int, document_type_id: int
) -> DocumentType:
    dt = db.get(DocumentType, document_type_id)
    if dt is None or (dt.origin is DocumentTypeOrigin.CUSTOM and dt.organization_id != organization_id):
        raise NotFound("DocumentType not found")
    if dt.origin is DocumentTypeOrigin.CANONICAL:
        raise Forbidden("Use the deactivate-canonical endpoint for canonical types",
                       details={"code": "canonical_type_immutable"})
    if dt.status is DocumentTypeStatus.ARCHIVED:
        raise Conflict("Already archived", details={"code": "already_archived"})
    dt.status = DocumentTypeStatus.ARCHIVED
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="document_type.archived",
        entity_type="document_type",
        entity_id=dt.id,
        metadata={},
    )
    db.commit()
    db.refresh(dt)
    return dt


def restore_custom(
    db: Session, *, organization_id: int, actor_user_id: int, document_type_id: int
) -> DocumentType:
    dt = db.get(DocumentType, document_type_id)
    if dt is None or (dt.origin is DocumentTypeOrigin.CUSTOM and dt.organization_id != organization_id):
        raise NotFound("DocumentType not found")
    if dt.origin is DocumentTypeOrigin.CANONICAL:
        raise Forbidden("Use the activate-canonical endpoint for canonical types",
                       details={"code": "canonical_type_immutable"})
    if dt.status is DocumentTypeStatus.ACTIVE:
        return dt
    dt.status = DocumentTypeStatus.ACTIVE
    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="document_type.restored",
        entity_type="document_type",
        entity_id=dt.id,
        metadata={},
    )
    db.commit()
    db.refresh(dt)
    return dt


def delete_custom(
    db: Session, *, organization_id: int, actor_user_id: int, document_type_id: int
) -> None:
    dt = db.get(DocumentType, document_type_id)
    if dt is None or (dt.origin is DocumentTypeOrigin.CUSTOM and dt.organization_id != organization_id):
        raise NotFound("DocumentType not found")
    if dt.origin is DocumentTypeOrigin.CANONICAL:
        raise Forbidden("Canonical DocumentTypes cannot be deleted",
                       details={"code": "canonical_type_immutable"})

    doc_count = db.execute(
        select(func.count()).select_from(Document).where(Document.document_type_id == dt.id)
    ).scalar_one()
    req_count = db.execute(
        select(func.count())
        .select_from(SupplierTypeDocumentRequirement)
        .where(SupplierTypeDocumentRequirement.document_type_id == dt.id)
    ).scalar_one()
    if doc_count > 0 or req_count > 0:
        raise Conflict(
            "Cannot delete a DocumentType with documents or requirements; archive it instead",
            details={
                "code": "has_dependencies",
                "documents_count": int(doc_count),
                "requirements_count": int(req_count),
            },
        )

    _audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="document_type.deleted",
        entity_type="document_type",
        entity_id=dt.id,
        metadata={"name": dt.name},
    )
    db.delete(dt)
    db.commit()


def _slugify(text: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", no_accents).strip("-").lower()
    return slug or "tipo"
