"""Bootstrap a new Organization with its default catalog state.

Invoked at the end of the OIDC callback that creates the first user of a new
tenant. Idempotent: safe to call multiple times.

Concretely:
    1. Seeds the SupplierType "Sin clasificar" (origin='system').
    2. Creates a SupplierTypeDocumentRequirement for every active canonical
       DocumentType, inheriting its periodicity.
    3. Marks every canonical DocumentType as active in TenantDocumentTypeSetting.

Phase 3 wires the SQLAlchemy models; this module defines the contract so the
OIDC flow can call it once the models exist.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from repse.catalog.canonical import CANONICAL_DOCUMENT_TYPES
from repse.logging import get_logger

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
    canonical_doc_types_activated: int
    requirements_created: int


def provision_organization(db: Session, organization_id: int) -> ProvisioningResult:
    """Idempotent provisioning of a tenant's default catalog state.

    Phase 3 implements the actual ORM operations against `supplier_types`,
    `supplier_type_document_requirements`, `document_types` and
    `tenant_document_type_settings`. Until those models exist this function
    raises NotImplementedError so calling code fails loudly instead of silently
    leaving a tenant under-provisioned.
    """
    # Defer the heavy implementation to Phase 3 where the models are defined.
    raise NotImplementedError(
        "provision_organization requires Phase 3 models. Wire up once "
        "SupplierType / SupplierTypeDocumentRequirement / DocumentType / "
        "TenantDocumentTypeSetting are merged."
    )


def required_canonical_slugs() -> list[str]:
    """Canonical slugs that a freshly provisioned tenant must reference."""
    return [ct.slug for ct in CANONICAL_DOCUMENT_TYPES]
