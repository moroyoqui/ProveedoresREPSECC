# Phase 1 Data Model: Vista de Cumplimiento Anual del Proveedor

**Sin cambios al schema relacional.** Este spec es de solo lectura. Consume las entidades ya definidas en el [data-model del 001](../001-repse-compliance-tracker/data-model.md).

| Entidad | Definida en | Rol en 006 |
|---------|-------------|------------|
| `Supplier` | 001 | Entrada principal; determina `supplier_type_id`. |
| `SupplierType` | 001 | Su catálogo de requisitos define las filas de la cuadrícula. |
| `SupplierTypeDocumentRequirement` | 001 | Enumera los pares (SupplierType, DocumentType) con `periodicity_override`. |
| `DocumentType` | 001 | Proporciona `name`, `periodicity` por defecto y si es `none` (sección separada). |
| `Document` | 001 | Proporciona los datos de cada celda: `coverage_period_start`, `status`, `verified`, `is_latest`. |

---

## Lógica computada: `cell_status`

La función `cell_status(doc, month, year, today)` que implementa `compliance/service.py`:

```
Inputs:
  doc       — Document | None  (el registro más reciente con is_latest=TRUE
                                para (supplier, doc_type, coverage_period))
  month     — int (1-12)
  year      — int
  today     — date

Output: CellStatus literal

Rules (en orden de prioridad):
  1. Si el mes no es un período de inicio para la periodicidad → "not_required"
  2. Si doc is not None:
       a. doc.status == "expired"                          → "expired"
       b. doc.verified == True                             → "validated"
       c. doc.verified == False                            → "submitted"
  3. Si doc is None:
       a. date(year, month, 1) > today                    → "future"
       b. date(year, month, 1) == date(today.year, today.month, 1) → "pending"
       c. date(year, month, 1) < date(today.year, today.month, 1) → "missing"
```

---

## Query de base (pseudocódigo SQLAlchemy)

```python
# Paso 1: obtener los requisitos activos del tipo de proveedor del supplier
requirements = (
    select(SupplierTypeDocumentRequirement, DocumentType)
    .join(DocumentType)
    .where(
        SupplierTypeDocumentRequirement.supplier_type_id == supplier.supplier_type_id,
        SupplierTypeDocumentRequirement.organization_id == org_id,
        SupplierTypeDocumentRequirement.status == "active",
    )
)

# Paso 2: obtener los documentos del año para este proveedor
documents = (
    select(Document)
    .where(
        Document.organization_id == org_id,
        Document.supplier_id == supplier_id,
        Document.is_latest == True,
        Document.deleted_at.is_(None),
        extract("year", Document.coverage_period_start) == year,
    )
)
# Indexado por (document_type_id, coverage_period_start) en memoria Python
# para construir la cuadrícula sin N+1 queries.
```

---

## Sin migration

No se requiere migration nueva para este spec.
