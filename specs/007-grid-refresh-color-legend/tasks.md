# Tasks: Grid Refresh & Color Legend (007)

**Input**: Design documents from `specs/007-grid-refresh-color-legend/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · quickstart.md ✅

**Tests**: No solicitados en el spec — omitidos.

**Scope**: 3 archivos frontend · 5 tareas · 0 cambios de backend.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin bloqueos)
- **[US#]**: Historia de usuario a la que pertenece la tarea

---

## Phase 1: User Story 1 — Refresco del grid al subir un documento (Priority: P1) 🎯 MVP

**Goal**: Al cerrar `UploadDialog` con éxito, la cuadrícula anual de cumplimiento se refresca automáticamente sin recargar la página.

**Independent Test**: Abrir el detalle de un proveedor, hacer clic en una celda "Faltante" para subir un documento, completar la carga — la celda debe cambiar de estado sin que el usuario recargue.

### Implementación US1

- [x] T001 [US1] Agregar invalidación de caché de compliance en `UploadDialog.onSuccess` en `frontend/src/components/documents/UploadDialog.tsx`: añadir `qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] })` junto a la invalidación existente de `["supplier", supplierId]`

**Checkpoint**: Con T001 completo, la cuadrícula se refresca al cerrar el diálogo de carga.

---

## Phase 2: User Story 2 — Leyenda de colores visible en el grid (Priority: P1)

**Goal**: Un recuadro con borde, fondo neutro y título "Leyenda" muestra los 7 estados de celda (color + etiqueta) junto a la cuadrícula, siempre visible en escritorio.

**Independent Test**: Abrir el detalle de cualquier proveedor — debajo del grid debe aparecer el recuadro "Leyenda" con 7 ítems incluyendo "No aplica", y los colores deben coincidir visualmente con los del grid.

### Implementación US2

- [x] T002 [P] [US2] Agregar el ítem `not_required` a `COMPLIANCE_LEGEND` en `frontend/src/components/suppliers/ComplianceCell.tsx`: añadir `{ status: "not_required", label: "No aplica" }` al final del array exportado

- [x] T003 [US2] Rediseñar el componente `ComplianceLegend` en `frontend/src/components/suppliers/ComplianceGrid.tsx` (depende de T002):
  - Añadir función helper `LegendSwatch({ status })` que para `not_required` renderiza `<span className="inline-block h-3 w-3 flex-shrink-0 rounded-full border border-dashed border-neutral-300 bg-neutral-100" />` y para los demás estados delega en `<ComplianceCell status={status} size="sm" />`
  - Reemplazar la lista `flex flex-wrap` actual por un `<div>` con `rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3`
  - Agregar título `<p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">Leyenda</p>`
  - Cambiar la `<ul>` a `grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3 lg:grid-cols-4`
  - Usar `<LegendSwatch status={item.status} />` en cada `<li>` en lugar de `<ComplianceCell status={item.status} size="sm" />`

**Checkpoint**: Con T002 + T003 completos, la leyenda muestra 7 estados dentro de un recuadro con borde y título.

---

## Phase 3: Polish & Verificación

**Purpose**: Confirmar consistencia visual entre leyenda y grid, y comportamiento responsive.

- [x] T004 [P] Verificar consistencia visual: comparar cada color del recuadro "Leyenda" con la celda correspondiente en el grid del proveedor — deben ser idénticos. Si hay discrepancia, ajustar clases Tailwind en `LegendSwatch` o en `ComplianceCell` según corresponda
- [x] T005 [P] Verificar comportamiento responsive de la leyenda a < 768 px: en vista móvil la cuadrícula de la leyenda debe colapsar a menos columnas (el grid `grid-cols-2` lo maneja automáticamente con las clases `sm:` y `lg:`); confirmar que no hay overflow horizontal

**Checkpoint**: Leyenda y refresco verificados en escritorio y móvil.

---

## Dependencies & Execution Order

### Dependencias entre tareas

- **T001**: Independiente — puede comenzar inmediatamente
- **T002**: Independiente — puede ejecutarse en paralelo con T001
- **T003**: Depende de T002 (importa `COMPLIANCE_LEGEND` actualizado de `ComplianceCell.tsx`)
- **T004**: Depende de T001, T002, T003
- **T005**: Depende de T003

### Oportunidades de paralelismo

- **T001 ∥ T002**: Archivos distintos, sin dependencias mutuas — ejecutar en paralelo
- **T004 ∥ T005**: Ambas son verificaciones independientes

---

## Parallel Example

```text
# Ronda 1 — ejecutar en paralelo:
T001: UploadDialog.tsx — invalidación de compliance
T002: ComplianceCell.tsx — agregar not_required a COMPLIANCE_LEGEND

# Ronda 2 — tras completar T002:
T003: ComplianceGrid.tsx — LegendSwatch + rediseño ComplianceLegend

# Ronda 3 — tras completar T001, T002, T003:
T004: Verificar colores leyenda vs grid
T005: Verificar responsive < 768 px
```

---

## Implementation Strategy

### MVP (mínimo viable demostrable)

1. T001 → refresco del grid funcional
2. T002 + T003 → leyenda con 7 estados en recuadro
3. **STOP y VALIDA**: seguir el flujo del `quickstart.md`

### Entrega incremental

- US1 (T001) es un cambio de una línea — se puede entregar solo y ya aporta valor
- US2 (T002 + T003) es independiente — se puede entregar antes, después o a la vez que US1

---

## Notes

- Sin cambios de backend; sin nuevas dependencias npm
- El `[P]` en T002 significa que puede ejecutarse simultáneamente con T001 por ser archivos distintos
- Verificar que la importación de `COMPLIANCE_LEGEND` en `ComplianceGrid.tsx` no necesita cambios (ya la importa con `{ COMPLIANCE_LEGEND, ComplianceCell }`)
- Total: **5 tareas** · **2 user stories P1** · **3 archivos frontend**
