# Implementation Plan: Grid Refresh & Color Legend

**Branch**: `007-grid-refresh-color-legend` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-grid-refresh-color-legend/spec.md`

## Summary

Dos mejoras de usabilidad sobre la cuadrícula anual de cumplimiento del proveedor (spec 006):

1. **Refresco automático del grid**: Al cerrar `UploadDialog` con éxito, se invalida la clave de caché `["supplier-compliance", supplierId]` con React Query, disparando una nueva fetch del endpoint `GET /api/v1/suppliers/{id}/compliance?year=YYYY`. Un cambio de una sola línea en `UploadDialog.tsx`.

2. **Leyenda de colores**: El componente `ComplianceLegend` ya existe en `ComplianceGrid.tsx` pero carece de encuadre visual y le falta el séptimo estado (`not_required`). Se agrega el ítem y se rediseña como un recuadro con borde, fondo y título "Leyenda".

**Sin cambios de backend.** Sin nuevas dependencias. Tres archivos frontend.

## Technical Context

**Language/Version**: TypeScript 5.x + React 18

**Primary Dependencies**: React Query (TanStack Query) para invalidación de caché; Tailwind CSS para estilos

**Storage**: N/A (no persistencia nueva)

**Testing**: Vitest + Playwright E2E (existentes)

**Target Platform**: Web desktop (≥ 1280 px principal); responsive para < 768 px (leyenda compacta)

**Project Type**: Web application (frontend SPA + FastAPI backend)

**Performance Goals**: El refresco del grid debe completarse en < 3 s en red estándar (reutiliza endpoint ya optimizado)

**Constraints**: Sin cambios de backend; sin dependencias nuevas; sin nuevas tablas

**Scale/Scope**: 3 archivos frontend modificados, ~30 líneas de cambio total

## Constitution Check

*Re-evaluado después del diseño (Phase 1).*

| Principio | Estado | Nota |
|---|---|---|
| I. Secure by Default | ✅ PASS | Sin nuevos endpoints; no hay superficies de ataque nuevas |
| II. Multi-Tenant Data Isolation | ✅ PASS | Sin cambios en modelo de datos ni en queries del backend |
| III. Test-First for Critical Paths | ✅ PASS | No hay lógica de auth/billing/tenant; la invalidación de caché se cubre en E2E |
| IV. Simplicity (YAGNI) | ✅ PASS | Cambio mínimo: 1 línea en UploadDialog, extensión de array + rediseño visual |

Sin violaciones. No se requiere sección de Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-grid-refresh-color-legend/
├── plan.md          ← este archivo
├── research.md      ← hallazgos de auditoría del código existente
├── data-model.md    ← entidades afectadas y flujo de caché
├── quickstart.md    ← guía de implementación paso a paso
├── checklists/
│   └── requirements.md
└── tasks.md         ← generado por /speckit-tasks (pendiente)
```

### Source Code (archivos afectados)

```text
frontend/
└── src/
    ├── components/
    │   ├── documents/
    │   │   └── UploadDialog.tsx          ← agregar invalidación compliance
    │   └── suppliers/
    │       ├── ComplianceCell.tsx        ← agregar not_required a COMPLIANCE_LEGEND
    │       └── ComplianceGrid.tsx        ← rediseñar ComplianceLegend
    └── (sin cambios en pages/ ni lib/)
```

**Structure Decision**: Web app (Option 2). Solo frontend; backend sin cambios.

## Design Details

### US1 — Refresco del grid (cambio en `UploadDialog.tsx`)

**Archivo**: `frontend/src/components/documents/UploadDialog.tsx`

**Cambio**: En el bloque `onSuccess` del mutation, agregar:
```typescript
qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] });
```
junto a la invalidación existente de `["supplier", supplierId]`.

**Mecanismo**: React Query invalida por prefijo — cualquier query cuya clave empiece con `["supplier-compliance", supplierId]` se marca como stale y se re-fetcha. Esto incluye `["supplier-compliance", supplierId, 2026]` y cualquier otro año que esté cacheado.

**Comportamiento en caso de error**: La invalidación solo ocurre en `onSuccess`; si la carga falla, `onError` se ejecuta y no hay invalidación (FR-004 cumplido automáticamente).

### US2 — Leyenda de colores (cambios en `ComplianceCell.tsx` y `ComplianceGrid.tsx`)

**Archivo 1**: `frontend/src/components/suppliers/ComplianceCell.tsx`

**Cambio**: Agregar `{ status: "not_required", label: "No aplica" }` al final de `COMPLIANCE_LEGEND`.

**Archivo 2**: `frontend/src/components/suppliers/ComplianceGrid.tsx`

**Cambio**: Refactorizar el componente interno `ComplianceLegend`:
- Envolver en `<div>` con clases `rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3`
- Agregar título `<p>Leyenda</p>` con estilo `text-xs font-semibold uppercase tracking-wide text-neutral-400`
- Cambiar lista de `flex flex-wrap` a `grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3 lg:grid-cols-4`
- Agregar helper `LegendSwatch` que para `not_required` renderiza un `<span>` con borde punteado en lugar de usar `ComplianceCell` (que renderiza vacío para ese estado)

**Diseño del recuadro:**
```
┌─────────────────────────────────────────────────────────┐
│ LEYENDA                                                 │
│  ● Validado          ● Pendiente de validación          │
│  ● Vencido           ● Faltante                         │
│  ● En plazo          ● Mes futuro                       │
│  ○ No aplica                                            │
└─────────────────────────────────────────────────────────┘
```
(● = círculo sólido con color; ○ = círculo con borde punteado gris)
