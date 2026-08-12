"""Bootstrap a new Organization with its default catalog state.

Idempotent: safe to call multiple times.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.alerts.models import AlertConfig
from repse.db.tenant_filter import with_admin_scope
from repse.document_types.models import DocumentType, DocumentTypeOrigin, DocumentTypeStatus
from repse.logging import get_logger
from repse.organizations.models import Organization
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierType,
    SupplierTypeDocumentRequirement,
    SupplierTypeOrigin,
    SupplierTypeStatus,
)

log = get_logger(__name__)

SYSTEM_SUPPLIER_TYPE_NAME = "Sin clasificar"
SYSTEM_SUPPLIER_TYPE_DESCRIPTION = (
    "Tipo por defecto sembrado por el sistema. Exige el catálogo canónico completo del tenant. "
    "Inmutable: no puede eliminarse, archivarse ni renombrarse."
)


@dataclass(frozen=True)
class ProvisioningResult:
    organization_id: int
    sin_clasificar_id: int
    requirements_created: int


def provision_organization(db: Session, organization_id: int) -> ProvisioningResult:
    """Seed 'Sin clasificar' SupplierType + requirements for every canonical DocumentType.

    Skips work that already exists (idempotent). Uses with_admin_scope so the
    TenantOwned filter doesn't fail before tenant context is set.
    """
    with with_admin_scope():
        sin_clasificar = db.execute(
            select(SupplierType).where(
                SupplierType.organization_id == organization_id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one_or_none()

        if sin_clasificar is None:
            sin_clasificar = SupplierType(
                organization_id=organization_id,
                name=SYSTEM_SUPPLIER_TYPE_NAME,
                description=SYSTEM_SUPPLIER_TYPE_DESCRIPTION,
                origin=SupplierTypeOrigin.SYSTEM,
                status=SupplierTypeStatus.ACTIVE,
            )
            db.add(sin_clasificar)
            db.flush()

        canonical_types = db.execute(
            select(DocumentType).where(
                DocumentType.origin == DocumentTypeOrigin.CANONICAL,
                DocumentType.status == DocumentTypeStatus.ACTIVE,
            )
        ).scalars().all()

        existing_pairs = {
            row.document_type_id
            for row in db.execute(
                select(SupplierTypeDocumentRequirement).where(
                    SupplierTypeDocumentRequirement.supplier_type_id == sin_clasificar.id,
                )
            ).scalars()
        }

        created = 0
        for dt in canonical_types:
            if dt.id in existing_pairs:
                continue
            db.add(
                SupplierTypeDocumentRequirement(
                    organization_id=organization_id,
                    supplier_type_id=sin_clasificar.id,
                    document_type_id=dt.id,
                    periodicity_override=None,
                    status=RequirementStatus.ACTIVE,
                )
            )
            created += 1
        db.flush()

        # Seed the per-org alert configuration (spec 002, FR-007). Idempotent.
        existing_cfg = db.execute(
            select(AlertConfig).where(AlertConfig.organization_id == organization_id)
        ).scalar_one_or_none()
        if existing_cfg is None:
            org = db.execute(
                select(Organization).where(Organization.id == organization_id)
            ).scalar_one()
            db.add(
                AlertConfig(
                    organization_id=organization_id,
                    default_recipient_emails=[org.contact_email],
                )
            )
            db.flush()

        return ProvisioningResult(
            organization_id=organization_id,
            sin_clasificar_id=sin_clasificar.id,
            requirements_created=created,
        )
