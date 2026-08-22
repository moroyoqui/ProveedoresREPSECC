"""Compliance routes (spec 006 — GET /api/v1/suppliers/{id}/compliance)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.compliance import service
from repse.compliance.schemas import ComplianceGridOut
from repse.db.session import get_db
from repse.documents import service as documents_service
from repse.documents.models import Document
from repse.errors import NotFound, UnprocessableEntity, ValidationFailure
from repse.suppliers.models import Supplier
from repse.users.models import Role

router = APIRouter()


@router.get(
    "/suppliers/{supplier_id}/compliance",
    response_model=ComplianceGridOut,
)
def get_supplier_compliance(
    supplier_id: int,
    year: int | None = Query(None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> ComplianceGridOut:
    current_year = date.today().year
    effective_year = year if year is not None else current_year

    if effective_year < 2020 or effective_year > current_year:
        raise ValidationFailure(
            "Year out of allowed range",
            details={"code": "invalid_year", "min": 2020, "max": current_year},
        )

    return service.get_annual_compliance(
        db,
        supplier_id=supplier_id,
        organization_id=user.organization_id,
        year=effective_year,
    )


class ValidateCellIn(BaseModel):
    document_type_id: int
    coverage_period_start: date | None = None
    # Spec 017 (FR-012): la nota que ya existía al verificar un documento queda
    # disponible también al validar desde la rejilla.
    note: str | None = None


def _current_document(
    db: Session,
    *,
    organization_id: int,
    supplier_id: int,
    document_type_id: int,
    coverage_period_start: date | None,
) -> Document:
    """Documento vigente de una celda. Es único por (proveedor, tipo, período).

    Spec 017: la celda no guarda estado propio; su marca vive en este documento.
    Sin documento no hay nada que dar por bueno (FR-005).
    """
    doc = db.execute(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.supplier_id == supplier_id,
            Document.document_type_id == document_type_id,
            Document.coverage_period_start == coverage_period_start,
            Document.is_latest.is_(True),
            Document.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if doc is None:
        raise UnprocessableEntity(
            "Cell has no current document to validate",
            details={"code": "no_document_to_validate"},
        )
    return doc


def _supplier_or_404(db: Session, supplier_id: int, organization_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.organization_id != organization_id:
        raise NotFound("Supplier not found")
    return supplier


@router.post("/suppliers/{supplier_id}/compliance/validate")
def validate_document_type(
    supplier_id: int,
    body: ValidateCellIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> dict:
    """Valida una celda marcando como verificado su documento vigente (spec 017).

    Antes escribía en `compliance_cell_validations`, una marca paralela que podía
    contradecir a la del documento. Ahora ambas pantallas escriben en el mismo
    sitio, y el acto queda auditado, cosa que esta ruta no hacía.
    """
    _supplier_or_404(db, supplier_id, user.organization_id)

    doc = _current_document(
        db,
        organization_id=user.organization_id,
        supplier_id=supplier_id,
        document_type_id=body.document_type_id,
        coverage_period_start=body.coverage_period_start,
    )

    verified = documents_service.verify_document(
        db,
        document_id=doc.id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
        note=body.note,
    )
    return {
        "status": "validated",
        "validated_at": verified.verified_at.isoformat() if verified.verified_at else None,
        "document_id": verified.id,
    }


@router.post("/suppliers/{supplier_id}/compliance/unvalidate")
def unvalidate_document_type(
    supplier_id: int,
    body: ValidateCellIn,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value, Role.MANAGER.value)),
    db: Session = Depends(get_db),
) -> dict:
    """Retira la validación de una celda (spec 017, FR-006).

    No existía equivalente: la validación de celda era irreversible.
    """
    _supplier_or_404(db, supplier_id, user.organization_id)

    doc = _current_document(
        db,
        organization_id=user.organization_id,
        supplier_id=supplier_id,
        document_type_id=body.document_type_id,
        coverage_period_start=body.coverage_period_start,
    )

    documents_service.unverify_document(
        db,
        document_id=doc.id,
        organization_id=user.organization_id,
        actor_user_id=user.user_id,
    )
    return {"status": "unvalidated", "document_id": doc.id}
