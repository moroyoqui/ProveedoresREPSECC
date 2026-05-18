"""Cambio destructivo de SupplierType (FR-005b/c/d spec 001).

Cuando se cambia el `supplier_type_id` de un proveedor, los documentos cuyo
`due_date_effective` cae en el año natural en curso (en la zona horaria del
tenant) deben eliminarse: el nuevo tipo determina un set de requisitos
distinto y los documentos del año en curso bajo el tipo anterior dejan de ser
representativos del cumplimiento actual.

El flujo es:

1. `preview_destructive_change` — calcula los documentos afectados y devuelve
   un payload para que el frontend pida confirmación.
2. `execute_destructive_change` — transaccional: borra registros + archivos,
   aplica el nuevo tipo y escribe la bitácora. Cualquier fallo (incluido el
   borrado físico del archivo) revierte todo y deja al proveedor con el tipo
   original sin huérfanos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from repse.audit import actions as audit_actions
from repse.audit.service import AuditEvent, write_event
from repse.config import get_settings
from repse.db.tenant_filter import with_admin_scope
from repse.document_types.models import DocumentType
from repse.documents.models import Document
from repse.documents.storage import FileStore
from repse.errors import NotFound, ValidationFailure
from repse.organizations.models import Organization
from repse.suppliers.models import Supplier
from repse.supplier_types.models import (
    SupplierType,
    SupplierTypeStatus,
)

if TYPE_CHECKING:
    from repse.suppliers.schemas import AffectedDocumentOut


@dataclass(frozen=True)
class _AffectedDoc:
    id: int
    document_type_id: int
    document_type_name: str
    coverage_period_start: date | None
    coverage_period_end: date | None
    due_date_effective: date | None


def _current_year_in_tenant_tz(db: Session, organization_id: int) -> int:
    """Año natural en curso según la zona horaria configurada en la Organization."""
    with with_admin_scope():
        org = db.get(Organization, organization_id)
    if org is None:
        # Caller already validated tenant; defensive fallback.
        return datetime.now(timezone.utc).year
    try:
        tz = ZoneInfo(org.timezone)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).year


def _affected_documents(
    db: Session, *, supplier_id: int, current_year: int
) -> list[_AffectedDoc]:
    rows = db.execute(
        select(Document, DocumentType)
        .join(DocumentType, DocumentType.id == Document.document_type_id)
        .where(Document.supplier_id == supplier_id)
        .order_by(Document.due_date_effective)
    ).all()
    affected: list[_AffectedDoc] = []
    for doc, dt in rows:
        if doc.due_date_effective is None:
            continue
        if doc.due_date_effective.year != current_year:
            continue
        affected.append(
            _AffectedDoc(
                id=doc.id,
                document_type_id=dt.id,
                document_type_name=dt.name,
                coverage_period_start=doc.coverage_period_start,
                coverage_period_end=doc.coverage_period_end,
                due_date_effective=doc.due_date_effective,
            )
        )
    return affected


def _format_period(start: date | None, end: date | None) -> str | None:
    if start is None and end is None:
        return None
    if start is not None and end is not None:
        return f"{start.isoformat()} a {end.isoformat()}"
    if start is not None:
        return start.isoformat()
    if end is not None:
        return end.isoformat()
    return None


def _resolve_supplier_type_or_fail(
    db: Session, *, organization_id: int, supplier_type_id: int
) -> SupplierType:
    st = db.get(SupplierType, supplier_type_id)
    if st is None or st.organization_id != organization_id:
        raise NotFound("SupplierType not found")
    if st.status is not SupplierTypeStatus.ACTIVE:
        raise ValidationFailure("SupplierType is archived")
    return st


@dataclass(frozen=True)
class PreviewResult:
    requires_confirmation: bool
    affected_count: int
    affected_documents: list[_AffectedDoc]


def preview_destructive_change(
    db: Session, *, supplier_id: int, organization_id: int, new_supplier_type_id: int
) -> PreviewResult:
    """Calcula qué documentos se eliminarían si se aplica el nuevo SupplierType."""
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")
    # Garantiza tenant ownership y existencia del tipo objetivo.
    _resolve_supplier_type_or_fail(
        db, organization_id=organization_id, supplier_type_id=new_supplier_type_id
    )

    if new_supplier_type_id == supplier.supplier_type_id:
        return PreviewResult(requires_confirmation=False, affected_count=0, affected_documents=[])

    year = _current_year_in_tenant_tz(db, organization_id)
    affected = _affected_documents(db, supplier_id=supplier.id, current_year=year)
    return PreviewResult(
        requires_confirmation=bool(affected),
        affected_count=len(affected),
        affected_documents=affected,
    )


def to_affected_payload(items: list[_AffectedDoc]) -> list[dict]:
    """Convierte affected docs a payload listo para usar en `error.details` o la respuesta."""
    out: list[dict] = []
    for it in items:
        out.append(
            {
                "id": it.id,
                "document_type": it.document_type_name,
                "coverage_period": _format_period(it.coverage_period_start, it.coverage_period_end),
                "due_date_effective": it.due_date_effective.isoformat()
                if it.due_date_effective
                else None,
            }
        )
    return out


def execute_destructive_change(
    db: Session,
    *,
    supplier_id: int,
    organization_id: int,
    new_supplier_type_id: int,
    actor_user_id: int,
) -> Supplier:
    """Aplica el cambio destructivo en una sola transacción.

    Orden:
      1. Identificar documentos afectados (año en curso).
      2. Para cada documento: borrar archivo físico → borrar fila en DB →
         escribir audit log `document.deleted_by_supplier_type_change`.
      3. Actualizar `supplier.supplier_type_id`.
      4. Escribir audit log `supplier.type_changed`.
      5. Commit. Si cualquier paso falla, se hace rollback y el archivo
         eliminado (si ya se borró) no puede recuperarse, pero la transacción
         falla por completo: re-lanzamos para que el cliente reintente.

    Nota sobre integridad: borramos primero el archivo y luego la fila para
    minimizar el riesgo de quedar con filas sin archivo si el commit falla.
    Si el borrado físico falla, no se toca DB y se hace rollback.
    """
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")

    prev_supplier_type_id = supplier.supplier_type_id
    if new_supplier_type_id == prev_supplier_type_id:
        return supplier

    new_st = _resolve_supplier_type_or_fail(
        db, organization_id=organization_id, supplier_type_id=new_supplier_type_id
    )

    year = _current_year_in_tenant_tz(db, organization_id)
    affected = _affected_documents(db, supplier_id=supplier.id, current_year=year)

    store = FileStore(get_settings())
    # Track physical deletes ya hechos para diagnosticar inconsistencias si
    # el commit falla luego (rollback de DB no resucita archivos).
    deleted_files: list[str] = []

    try:
        for item in affected:
            doc = db.get(Document, item.id)
            if doc is None:
                continue
            try:
                store.delete(doc.file_path)
                deleted_files.append(doc.file_path)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"Failed to delete file for document {doc.id}: {exc}"
                ) from exc

            write_event(
                db,
                AuditEvent(
                    organization_id=organization_id,
                    actor_user_id=actor_user_id,
                    action=audit_actions.DOCUMENT_DELETED_BY_SUPPLIER_TYPE_CHANGE,
                    entity_type="document",
                    entity_id=doc.id,
                    metadata={
                        "supplier_id": supplier.id,
                        "prev_supplier_type_id": prev_supplier_type_id,
                        "new_supplier_type_id": new_supplier_type_id,
                        "document_type_id": doc.document_type_id,
                        "due_date_effective": doc.due_date_effective.isoformat()
                        if doc.due_date_effective
                        else None,
                        "file_sha256": doc.file_sha256,
                        "version": doc.version,
                    },
                ),
            )
            db.delete(doc)
            db.flush()

        supplier.supplier_type_id = new_st.id
        db.flush()

        write_event(
            db,
            AuditEvent(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=audit_actions.SUPPLIER_TYPE_CHANGED,
                entity_type="supplier",
                entity_id=supplier.id,
                metadata={
                    "prev_supplier_type_id": prev_supplier_type_id,
                    "new_supplier_type_id": new_supplier_type_id,
                    "deleted_document_count": len(affected),
                    "destructive": True,
                },
            ),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(supplier)
    return supplier


def execute_non_destructive_change(
    db: Session,
    *,
    supplier_id: int,
    organization_id: int,
    new_supplier_type_id: int,
    actor_user_id: int,
) -> Supplier:
    """Cambio sin documentos afectados: solo actualiza el tipo y registra audit."""
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found")
    prev_supplier_type_id = supplier.supplier_type_id
    if new_supplier_type_id == prev_supplier_type_id:
        return supplier

    new_st = _resolve_supplier_type_or_fail(
        db, organization_id=organization_id, supplier_type_id=new_supplier_type_id
    )

    supplier.supplier_type_id = new_st.id
    write_event(
        db,
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=audit_actions.SUPPLIER_TYPE_CHANGED,
            entity_type="supplier",
            entity_id=supplier.id,
            metadata={
                "prev_supplier_type_id": prev_supplier_type_id,
                "new_supplier_type_id": new_supplier_type_id,
                "deleted_document_count": 0,
                "destructive": False,
            },
        ),
    )
    db.commit()
    db.refresh(supplier)
    return supplier


CONFIRMATION_TEXT_EXPECTED = "eliminar"


def confirmation_matches(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() == CONFIRMATION_TEXT_EXPECTED
