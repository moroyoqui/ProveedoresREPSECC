# Data Model: Nombre de Contacto y Registro REPSE en Proveedor

**Feature**: 011-supplier-contact-repse  
**Date**: 2026-06-08

---

## Entidades afectadas

### `suppliers` (modificada)

Tabla existente. Esta feature añade una columna y completa la exposición de campos ya existentes que no se estaban devolviendo en las respuestas de la API.

| Columna | Tipo | Nullable | Nuevo | Descripción |
|---------|------|----------|-------|-------------|
| `contact_name` | VARCHAR(255) | YES | No | Nombre de la persona de contacto del proveedor. Ya existía en el modelo y en los schemas de escritura (`SupplierIn`, `SupplierPatch`). No estaba en `SupplierDetailOut` ni en el formulario de edición. |
| `repse_folio` | VARCHAR(60) | YES | **Sí** | Número de folio de registro REPSE emitido por la STPS. Texto libre, sin validación de formato. |

**Sin cambios de cardinalidad ni relaciones.** El campo `repse_folio` no referencia ninguna otra tabla.

---

## Migración Alembic

**Revisión**: `0008_add_repse_folio`  
**Predecesor**: `0007_add_sectors_giros`

```sql
-- upgrade
ALTER TABLE suppliers
    ADD COLUMN repse_folio VARCHAR(60) NULL DEFAULT NULL AFTER notes;

-- downgrade
ALTER TABLE suppliers DROP COLUMN repse_folio;
```

Sin índice: `repse_folio` no se usa como filtro de consulta en esta feature.

---

## Validaciones

| Campo | Regla | Error |
|-------|-------|-------|
| `contact_name` | max 120 caracteres (spec); modelo usa 255 — se limita en Pydantic a 120 | 422 |
| `repse_folio` | max 60 caracteres | 422 |
| Ambos | opcionales (nullable) | — |

**Nota sobre max_length de `contact_name`**: La spec dice 120 caracteres; el modelo backend tiene `String(255)`. La validación Pydantic usará `max_length=120` para no romper datos existentes más largos; el modelo de BD no se reduce. Si en el futuro se detectan datos existentes > 120 chars, se revisará.

---

## Estado previo vs. posterior por capa

| Capa | `contact_name` antes | `contact_name` después | `repse_folio` antes | `repse_folio` después |
|------|---------------------|----------------------|--------------------|-----------------------|
| Modelo SQLAlchemy | ✅ existe | sin cambio | ❌ no existe | ✅ agregado |
| `SupplierIn` schema | ✅ existe | sin cambio | ❌ | ✅ agregado |
| `SupplierPatch` schema | ✅ existe | sin cambio | ❌ | ✅ agregado |
| `SupplierListItem` schema | ✅ existe | sin cambio | ❌ | ✅ agregado (opcional) |
| `SupplierDetailOut` schema | ❌ faltaba | ✅ agregado | ❌ | ✅ agregado |
| `_serialize_detail` route | ❌ no mapeado | ✅ mapeado | ❌ | ✅ mapeado |
| `PortalComplianceGridOut` | ❌ N/A | sin cambio | ❌ | ✅ campo top-level |
| Frontend `SupplierCreate` | ✅ existe | sin cambio | ❌ | ✅ agregado |
| Frontend `SupplierPatch` | ✅ existe | sin cambio | ❌ | ✅ agregado |
| Frontend `SupplierDetail` | ❌ no en tipo | ✅ en tipo | ❌ | ✅ en tipo |
| Frontend `ComplianceGrid` | ❌ N/A | sin cambio | ❌ | ✅ campo opcional |
| `new.tsx` | ✅ campo UI | sin cambio | ❌ | ✅ campo UI + schema |
| `edit.tsx` | ❌ sin estado/campo | ✅ estado + campo | ❌ | ✅ estado + campo |
| `detail.tsx` | ❌ no mostrado | ✅ mostrado | ❌ | ✅ mostrado |
| `portal/index.tsx` | ❌ N/A | sin cambio | ❌ | ✅ mostrado (solo lectura) |
