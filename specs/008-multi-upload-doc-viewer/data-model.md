# Data Model: Carga Múltiple y Visualizador de Documentos

**Feature**: 008-multi-upload-doc-viewer | **Date**: 2026-05-19

---

## Entidades existentes (sin cambios estructurales)

### Document
`documents` — ya definida en spec 001. El campo `verified` sigue existiendo para verificación de archivo individual (FR-016/FR-018), pero **ya no determina** el `CellStatus.VALIDATED` de la celda.

### CellOut (schema de respuesta — actualización)

```python
class CellOut(BaseModel):
    month: int
    status: CellStatus          # VALIDATED ahora proviene de type_validated
    document_id: int | None
    document_count: int = 0
    coverage_period_start: date | None
    type_validated: bool = False  # ← NUEVO (Phase 8)
```

---

## Entidad nueva: ComplianceCellValidation

### Tabla: `compliance_cell_validations`

| Columna | Tipo | Nullable | Descripción |
|---|---|---|---|
| `id` | BIGINT PK | No | Auto-increment |
| `organization_id` | BIGINT | No | Tenant; no FK (consistencia con pattern de TenantOwned) |
| `supplier_id` | BIGINT FK→suppliers | No | CASCADE DELETE |
| `document_type_id` | BIGINT FK→document_types | No | RESTRICT DELETE |
| `coverage_period_start` | DATE | Sí | NULL para requisitos de entrega única (periodicity=none) |
| `validated_by` | BIGINT FK→users | Sí | SET NULL si usuario eliminado |
| `validated_at` | DATETIME | No | Momento de la validación |
| `created_at` | DATETIME | No | `CURRENT_TIMESTAMP(6)` |
| `updated_at` | DATETIME | No | `CURRENT_TIMESTAMP(6)` |

**Constraint único**: `uq_cell_validation` sobre `(organization_id, supplier_id, document_type_id, coverage_period_start)`.

### Reglas de negocio

- Una celda puede tener como máximo un registro de validación (el constraint único lo garantiza).
- Si el supervisor vuelve a hacer clic en "Marcar como Validado", el registro existente se actualiza (`validated_by`, `validated_at`); no se duplica.
- La eliminación de documentos de una celda no elimina el registro de validación; la validación persiste hasta que se implemente "desvalidar" (fuera de scope de este feature).
- Si el proveedor es eliminado (CASCADE), sus registros de validación también se eliminan.

### Estado de la celda con la nueva lógica

```
Si existe ComplianceCellValidation para (org, supplier, doc_type, period):
    CellStatus = VALIDATED

Si NO existe ComplianceCellValidation Y existe Document (is_latest=True):
    CellStatus = SUBMITTED  (antes era VALIDATED si doc.verified=True)

Si NO existe Document:
    CellStatus = MISSING | PENDING | FUTURE | EXPIRED  (lógica de fechas sin cambio)
```

---

## Relaciones

```
Organization (1) ──< ComplianceCellValidation (N)
Supplier     (1) ──< ComplianceCellValidation (N)
DocumentType (1) ──< ComplianceCellValidation (N)
User         (1) ──< ComplianceCellValidation (N)  [validated_by, nullable]
```
