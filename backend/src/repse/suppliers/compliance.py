"""Aggregate compliance counts for a supplier (T094 spec 001).

Devuelve ``{percent, counts: {valid, expiring_soon, expired, missing}}``.

Reglas:
  * ``missing`` se deriva de ``SupplierType.requirements`` (status=active) que
    no tienen ``Document(is_latest=True)`` para el ``document_type``. FR-012b.
  * Cuenta sólo los documentos cuyo ``document_type_id`` está en los
    requirements activos (canónicos no exigidos por el tipo del proveedor se
    ignoran, aunque existan documentos históricos).
  * ``percent = round(valid * 100 / total)`` donde ``total`` es la suma de los
    cuatro conteos. Si total=0 → percent=0.

Multi-tenant: el caller debe haber establecido ``current_tenant`` (vía
``set_current_tenant`` o por estar dentro de un request HTTP).
"""

from __future__ import annotations

from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.documents.models import Document, DocumentStatus
from repse.errors import NotFound
from repse.suppliers.models import Supplier
from repse.supplier_types.models import (
    RequirementStatus,
    SupplierTypeDocumentRequirement,
)


class ComplianceCounts(TypedDict):
    valid: int
    expiring_soon: int
    expired: int
    missing: int


class ComplianceAggregate(TypedDict):
    percent: int
    counts: ComplianceCounts


def aggregate(db: Session, *, supplier_id: int) -> ComplianceAggregate:
    """Calcula el agregado de cumplimiento para un proveedor."""
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")

    required_type_ids = set(
        db.execute(
            select(SupplierTypeDocumentRequirement.document_type_id).where(
                SupplierTypeDocumentRequirement.supplier_type_id
                == supplier.supplier_type_id,
                SupplierTypeDocumentRequirement.status == RequirementStatus.ACTIVE,
            )
        ).scalars()
    )

    counts: ComplianceCounts = {
        "valid": 0,
        "expiring_soon": 0,
        "expired": 0,
        "missing": 0,
    }

    if required_type_ids:
        # Documents latest del proveedor, restringidos a tipos requeridos.
        rows = db.execute(
            select(Document.document_type_id, Document.status).where(
                Document.supplier_id == supplier.id,
                Document.is_latest.is_(True),
                Document.document_type_id.in_(required_type_ids),
            )
        ).all()
    else:
        rows = []

    covered_type_ids: set[int] = set()
    for type_id, status in rows:
        key = status.value if isinstance(status, DocumentStatus) else str(status)
        if key in counts:
            counts[key] += 1  # type: ignore[literal-required]
        covered_type_ids.add(int(type_id))

    counts["missing"] = sum(
        1 for tid in required_type_ids if tid not in covered_type_ids
    )

    total = sum(counts.values())
    percent = 0 if total == 0 else round(counts["valid"] * 100 / total)
    return {"percent": percent, "counts": counts}
