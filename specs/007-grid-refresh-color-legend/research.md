# Research: Grid Refresh & Color Legend

**Feature**: 007-grid-refresh-color-legend
**Date**: 2026-05-19

---

## Hallazgo 1: Estado real del refresco del grid tras la carga

**Investigación**: Se revisó `UploadDialog.tsx` (onSuccess) y `detail.tsx` (claves de React Query).

**Hallazgo**:
- `UploadDialog.onSuccess` invalida **solo** `["supplier", supplierId]` (línea 38 de `UploadDialog.tsx`).
- La query del compliance grid tiene la clave `["supplier-compliance", supplierId, year]` (línea 30 de `detail.tsx`).
- Estas dos claves no comparten prefijo, así que la invalidación del UploadDialog **no** dispara el refresco del grid.

**Decisión**: Agregar en `UploadDialog.onSuccess` la invalidación `qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] })`. React Query usa matching por prefijo, por lo que invalida todos los años del proveedor (cualquier query que empiece con `["supplier-compliance", supplierId]`), que es el comportamiento correcto.

**Alternativas consideradas**:
- Pasar `year` como prop a `UploadDialog` e invalidar la clave exacta → más frágil; si el documento corresponde a un año distinto al visible, el grid no actualizaría. La invalidación por prefijo es más robusta.
- Callback `onUploadSuccess` en `detail.tsx` que haga la invalidación → añade indirección sin beneficio; el approach directo en `UploadDialog` es más simple y coherente.

---

## Hallazgo 2: Estado actual de la leyenda de colores

**Investigación**: Se revisó `ComplianceCell.tsx` y `ComplianceGrid.tsx`.

**Hallazgo**:
- `COMPLIANCE_LEGEND` (línea 118 de `ComplianceCell.tsx`) ya existe con **6 ítems** — falta `not_required`.
- `ComplianceLegend` (componente local en `ComplianceGrid.tsx`, línea 100) ya se renderiza debajo del grid.
- La presentación actual es una lista inline (`flex flex-wrap`) **sin encuadre visual** — no tiene borde, fondo diferenciado ni título "Leyenda".
- El estado `not_required` tiene `COLOR["not_required"] = ""` (cadena vacía) — hay que representarlo visualmente de otra forma (círculo con borde punteado o gris muy claro).

**Decisiones**:
1. Agregar `not_required` a `COMPLIANCE_LEGEND` en `ComplianceCell.tsx`.
2. Rediseñar `ComplianceLegend` como un recuadro con borde, fondo neutro y título "Leyenda", reemplazando la lista inline por una cuadrícula compacta de dos columnas.
3. Para `not_required`: usar `bg-neutral-100 border border-dashed border-neutral-300` en la muestra de color, coherente con el estado "sin color" del grid.

**Alternativas consideradas**:
- Crear un componente separado `ComplianceLegend.tsx` → innecesario; el componente vive junto a `ComplianceGrid` que lo usa.
- Mostrar la leyenda en un tooltip o modal → viola FR-008 (debe estar siempre visible sin interacción en escritorio).

---

## Hallazgo 3: No se requieren cambios en backend

**Investigación**: Revisión de spec (Assumptions) y código del backend.

**Hallazgo**: Ambas mejoras son puramente del cliente (React Query cache invalidation + componente visual). El endpoint `GET /api/v1/suppliers/{id}/compliance?year=YYYY` ya existe y no requiere modificaciones.

**Decisión**: Cero cambios en backend. No hay nuevas tablas, endpoints ni migraciones.

---

## Resumen de decisiones

| Área | Decisión | Archivos afectados |
|---|---|---|
| Refresco grid | Invalidar `["supplier-compliance", supplierId]` en `UploadDialog.onSuccess` | `UploadDialog.tsx` |
| Leyenda — datos | Agregar `not_required` a `COMPLIANCE_LEGEND` | `ComplianceCell.tsx` |
| Leyenda — visual | Rediseñar `ComplianceLegend` como recuadro con borde, fondo y título | `ComplianceGrid.tsx` |
| Backend | Sin cambios | — |
