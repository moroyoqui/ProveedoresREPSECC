# Research: Catálogo de Sectores y Giros

**Feature**: 010-sector-giro-catalog
**Date**: 2026-06-08

---

## Decisión 1: Alcance de tenant para sectores y giros

**Decision**: Los catálogos `sectors` y `giros` son **globales** (no llevan `organization_id`). Son datos de referencia del sistema, no datos de cliente.

**Rationale**: El objetivo explícito de la feature es que todos los administradores compartan el mismo catálogo ("catálogos globales del sistema, compartidos entre todos los usuarios administradores; no son por cliente o por empresa"). Un catálogo por-tenant haría imposible la uniformidad en la clasificación entre organizaciones. El proyecto ya tiene precedente de datos no-tenant: la tabla `catalog` (tipos canónicos de documento).

**Alternatives considered**:
- Per-tenant (mismo patrón que `supplier_types`): descartado porque produciría catálogos duplicados e inconsistentes entre organizaciones.
- `organization_id = NULL` para registros globales: descartado por ambigüedad de esquema y complejidad de queries.

**Constitution note**: La excepción al principio II (Multi-Tenant Data Isolation) está justificada porque `sectors` y `giros` son tablas de referencia de solo-lectura para los procesos de negocio del tenant. El aislamiento de tenant se preserva en la tabla `suppliers`, donde las FKs `sector_id` y `giro_id` son atributos de un registro ya scoped por `organization_id`.

---

## Decisión 2: Ubicación de módulos backend

**Decision**: Dos módulos nuevos independientes: `repse/sectors/` y `repse/giros/`.

**Rationale**: El patrón del proyecto es un módulo por entidad de dominio (`supplier_types/`, `document_types/`, `suppliers/`). Agregar sectores y giros al módulo `catalog/` existente mezclaría responsabilidades con los tipos canónicos de documento. La separación facilita el testing unitario y la evolución independiente.

**Alternatives considered**:
- Módulo único `repse/sectors_giros/`: descartado; los nombres de entidad separados son más claros.
- Extender `repse/catalog/`: descartado; ese módulo gestiona tipos canónicos de documento, dominio diferente.

---

## Decisión 3: Estrategia de eliminación

**Decision**: Hard delete exclusivo. No hay soft-delete ni estado activo/inactivo.

**Rationale**: Clarificación Q1 del `/speckit-clarify`. Los catálogos de referencia sin histórico de cambio no necesitan soft-delete. Las protecciones de integridad referencial (RESTRICT en FK) son suficientes para prevenir pérdida de datos accidental.

**Alternatives considered**:
- Soft-delete con campo `deleted_at`: descartado por clarificación del usuario.
- Campo `is_active` boolean: descartado; genera ambigüedad (¿qué significa "inactivo"?) sin beneficio claro.

---

## Decisión 4: Integridad referencial en la base de datos

**Decision**: FKs con `ON DELETE RESTRICT` en todos los niveles jerárquicos.

**Rationale**:
- `giros.sector_id → sectors.id ON DELETE RESTRICT`: impide borrar un sector con giros.
- `suppliers.sector_id → sectors.id ON DELETE RESTRICT`: impide borrar un sector asignado a un proveedor (aunque el flujo normal ya previene esto vía FR-005).
- `suppliers.giro_id → giros.id ON DELETE RESTRICT`: impide borrar un giro asignado a un proveedor (FR-006).

La capa de aplicación valida antes de intentar el DELETE y devuelve mensajes de error amigables. El RESTRICT en DB es la red de seguridad.

---

## Decisión 5: Rutas API y prefijos

**Decision**: 
- Sectors: `/api/v1/sectors`
- Giros: `/api/v1/giros` (con query param `?sector_id=X` para filtrar)

**Rationale**: El patrón del proyecto monta routers con prefijos planos por entidad (`/api/v1/suppliers`, `/api/v1/supplier-types`, etc.). Usar `/api/v1/catalogs/sectors` añadiría un nivel de anidamiento innecesario (YAGNI). Los giros se listan globalmente con filtro opcional por sector, lo que simplifica el cliente frontend para el selector en cascada.

---

## Decisión 6: Control de acceso

**Decision**:
- `GET /sectors` y `GET /giros`: cualquier usuario autenticado (todos los roles internos).
- `POST/PATCH/DELETE /sectors` y `POST/PATCH/DELETE /giros`: solo rol `admin`.
- Vista en portal del proveedor: `GET /portal/compliance` extendido con `sector` y `giro` en solo lectura (rol `supplier`).

**Rationale**: La lista de sectores/giros es necesaria para que cualquier usuario interno pueda ver la clasificación de un proveedor. Las operaciones de escritura en catálogos de referencia son administrativas. La clarificación Q2 y Q3 del `/speckit-clarify` lo confirman.

---

## Decisión 7: Extensión del portal del proveedor

**Decision**: `GET /api/v1/portal/compliance` retorna dos campos nuevos en la raíz del objeto de respuesta: `sector` y `giro` (objetos con `id` y `name`, o `null`).

**Rationale**: El portal ya consulta los datos del proveedor para mostrar su cumplimiento. Agregar sector/giro al mismo endpoint no requiere un nuevo endpoint y minimiza el número de roundtrips desde el frontend del portal (YAGNI).

---

## Decisión 8: Migración Alembic

**Decision**: Una sola migración `0007_add_sectors_giros` que crea las tablas `sectors` y `giros` y altera `suppliers`.

**Rationale**: Los tres cambios son atómicos y co-dependientes (las FKs en `suppliers` referencian las nuevas tablas). Una sola migración es más segura y fácil de revertir.

---

## Decisión 9: Frontend — páginas de administración

**Decision**: Dos nuevas páginas en `frontend/src/pages/settings/catalogs/`: `sectors.tsx` y `giros.tsx`. Se acceden desde el `CatalogsHub` existente.

**Rationale**: El patrón del proyecto ya tiene `supplier-types.tsx` y `document-types.tsx` en esa carpeta. Las nuevas páginas siguen el mismo patrón de lista+acciones inline, sin modal de detalle separado (los catálogos son simples, no necesitan sub-rutas).

**Alternatives considered**:
- Página única combinada sectors+giros: más compleja de implementar y menos clara para el usuario.
- Modal de gestión: el patrón existente para supplier-types usa rutas separadas; mantener consistencia.
