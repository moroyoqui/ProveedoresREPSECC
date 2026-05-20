# Data Model: Grid Refresh & Color Legend

**Feature**: 007-grid-refresh-color-legend
**Date**: 2026-05-19

> Esta feature no introduce entidades nuevas ni cambios en el modelo de datos del backend.
> Los cambios son exclusivamente en la capa de presentación del cliente.

---

## Entidades existentes modificadas

### COMPLIANCE_LEGEND (array de configuración, frontend)

Definido en `frontend/src/components/suppliers/ComplianceCell.tsx`.

**Estado actual** (6 ítems):
```
validated  | submitted | expired | missing | pending | future
```

**Estado post-007** (7 ítems — se agrega `not_required`):
```
validated | submitted | expired | missing | pending | future | not_required
```

**Estructura de cada ítem** (sin cambios):
```typescript
{ status: CellStatus; label: string }
```

**Muestra visual por estado** (cómo se renderiza en la leyenda):

| Status | Clase Tailwind actual (ComplianceCell) | Representación en leyenda |
|---|---|---|
| `validated` | `bg-green-500` | Círculo verde sólido |
| `submitted` | `bg-yellow-400` | Círculo amarillo sólido |
| `expired` | `bg-red-700` | Círculo rojo oscuro sólido |
| `missing` | `bg-red-500` | Círculo rojo sólido |
| `pending` | `bg-gray-300` | Círculo gris medio sólido |
| `future` | `bg-gray-200` | Círculo gris claro sólido |
| `not_required` | `""` (sin clase) | Círculo con borde punteado `border border-dashed border-neutral-300 bg-neutral-100` |

---

## Flujo de invalidación de caché (React Query)

No es un cambio de modelo de datos, pero documenta el estado de las claves de caché relevantes:

| Query key | Qué carga | Cuándo se invalida (post-007) |
|---|---|---|
| `["supplier", supplierId]` | Datos básicos del proveedor (nombre, conteo, %) | Al subir documento (ya existía) |
| `["supplier-compliance", supplierId, year]` | Grid anual de cumplimiento | **Nuevo**: al subir documento, vía prefijo `["supplier-compliance", supplierId]` |
| `["documents-list"]` | Lista global de documentos | Sin cambios en este feature |

---

## Componentes afectados

| Componente | Archivo | Tipo de cambio |
|---|---|---|
| `UploadDialog` | `frontend/src/components/documents/UploadDialog.tsx` | Agregar invalidación de caché |
| `COMPLIANCE_LEGEND` | `frontend/src/components/suppliers/ComplianceCell.tsx` | Agregar ítem `not_required` |
| `ComplianceLegend` | `frontend/src/components/suppliers/ComplianceGrid.tsx` | Rediseñar presentación visual |
