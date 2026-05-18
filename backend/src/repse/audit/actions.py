"""Catálogo de acciones de auditoría (T128 spec 001).

Centraliza las cadenas usadas en `AuditLog.action` para evitar typos y permitir
búsqueda cruzada. Los servicios deben referenciar estas constantes en lugar de
literales.
"""

from __future__ import annotations

from typing import Final


# --- Supplier ---------------------------------------------------------------

SUPPLIER_CREATED: Final = "supplier.created"
SUPPLIER_UPDATED: Final = "supplier.updated"
SUPPLIER_DEACTIVATED: Final = "supplier.deactivated"
SUPPLIER_REACTIVATED: Final = "supplier.reactivated"
SUPPLIER_TYPE_CHANGED: Final = "supplier.type_changed"


# --- Document ---------------------------------------------------------------

DOCUMENT_UPLOADED: Final = "document.uploaded"
DOCUMENT_VERIFIED: Final = "document.verified"
DOCUMENT_UNVERIFIED: Final = "document.unverified"
DOCUMENT_OCR_COMPLETED: Final = "document.ocr_completed"
DOCUMENT_DELETED_BY_SUPPLIER_TYPE_CHANGE: Final = "document.deleted_by_supplier_type_change"


KNOWN_ACTIONS: Final[frozenset[str]] = frozenset(
    {
        SUPPLIER_CREATED,
        SUPPLIER_UPDATED,
        SUPPLIER_DEACTIVATED,
        SUPPLIER_REACTIVATED,
        SUPPLIER_TYPE_CHANGED,
        DOCUMENT_UPLOADED,
        DOCUMENT_VERIFIED,
        DOCUMENT_UNVERIFIED,
        DOCUMENT_OCR_COMPLETED,
        DOCUMENT_DELETED_BY_SUPPLIER_TYPE_CHANGE,
    }
)
