# Research: Validación de Tipo de Documento (US6 — Phase 8)

**Feature**: 008-multi-upload-doc-viewer | **Date**: 2026-05-19

---

## §1 — Almacenamiento de validaciones de tipo

**Decision**: Nueva tabla `compliance_cell_validations` con columnas `(organization_id, supplier_id, document_type_id, coverage_period_start)` + `UniqueConstraint`.

**Rationale**: La validación de tipo es una entidad de negocio distinta del documento. Guardarla en `documents` requeriría elegir un documento "representativo" en tipos multi-archivo, lo que es semánticamente incorrecto. Una tabla propia es la opción más directa, auditable y reversible.

**Alternatives considered**:
- Columna `type_validated` en `documents`: requeriría elegir el doc is_latest como portador del estado, pero un tipo puede no tener ningún doc is_latest si todos fueron eliminados. Rechazado.
- Campo en memoria (no persistido): el estado de validación debe sobrevivir recargas de página. Rechazado.
- Reutilizar `doc.verified` del documento is_latest para determinar VALIDATED: el usuario pidió explícitamente separar ambos conceptos. Rechazado (es el problema que esta feature resuelve).

---

## §2 — Cambio de comportamiento en `cell_status()`

**Decision**: `cell_status()` ya no devuelve `CellStatus.VALIDATED` basándose en `doc.verified`. La función devuelve `SUBMITTED` cuando existe un documento (independientemente de `verified`). El estado `VALIDATED` se aplica en `get_annual_compliance()` haciendo override del status cuando existe un registro en `compliance_cell_validations`.

**Rationale**: Separar la función de cálculo del estado bruto (`cell_status()`) del override por validación explícita (`get_annual_compliance()`) mantiene `cell_status()` simple y pura, y concentra la lógica de negocio nueva en un solo lugar.

**Migration concern**: Registros existentes con `doc.verified=True` perderán el estado VALIDATED hasta que un supervisor ejecute "Marcar como Validado". Si se necesita preservar el estado VALIDATED para registros ya verificados, ejecutar el siguiente script de backfill después de la migración:

```sql
INSERT IGNORE INTO compliance_cell_validations
  (organization_id, supplier_id, document_type_id, coverage_period_start, validated_by, validated_at, created_at, updated_at)
SELECT
  d.organization_id,
  d.supplier_id,
  d.document_type_id,
  d.coverage_period_start,
  d.verified_by,
  d.verified_at,
  NOW(),
  NOW()
FROM documents d
WHERE d.verified = TRUE
  AND d.is_latest = TRUE
  AND d.deleted_at IS NULL
  AND d.verified_by IS NOT NULL;
```

**Alternatives considered**:
- Mantener `cell_status()` devolviendo VALIDATED cuando `doc.verified=True` Y agregar type-level como un segundo camino a VALIDATED: mezcla los dos conceptos que el usuario quiere separar. Rechazado.

---

## §3 — Endpoint de validación: UPSERT vs. INSERT

**Decision**: UPSERT semántico en Python: buscar registro existente con `db.get()` o `select().where(...)`, actualizar si existe, crear si no existe.

**Rationale**: MySQL soporta `INSERT ... ON DUPLICATE KEY UPDATE` pero SQLAlchemy Core lo expone de forma dialecto-específica. El patrón Python es más legible y suficientemente eficiente para < 100k filas.

**Alternatives considered**:
- `INSERT IGNORE`: no actualiza `validated_by`/`validated_at` si el registro ya existe. Rechazado porque el supervisor puede querer re-validar y actualizar el actor/timestamp.

---

## §4 — Propagación del estado al frontend

**Decision**: `CellOut` incluye `type_validated: bool`. El frontend lee este campo para inicializar `localTypeValidated` en el modal. La mutación POST actualiza el estado local del modal (`setLocalTypeValidated(true)`) sin re-fetch del grid; el grid se refresca al cerrar el modal (mecanismo existente).

**Rationale**: Evita un segundo re-fetch del grid entero solo para actualizar el badge de una celda. El estado local en el modal es suficiente para la UX inmediata; el grid correcto se ve al cerrar.
