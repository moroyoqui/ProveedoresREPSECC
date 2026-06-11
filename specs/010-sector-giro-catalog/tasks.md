---

description: "Task list for 010-sector-giro-catalog implementation"
---

# Tasks: Catálogo de Sectores y Giros para Proveedores

**Input**: Design documents from `/specs/010-sector-giro-catalog/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/catalog-sectors-giros.md ✅

**Tests**: No incluidos (la especificación no los solicita explícitamente). Los contratos API y escenarios de aceptación de spec.md sirven como referencia para validación manual.

**Organization**: Tareas agrupadas por historia de usuario para implementación y prueba independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: Historia de usuario a la que pertenece la tarea (US1–US4)
- Cada tarea incluye la ruta exacta del archivo afectado

---

## Phase 1: Setup (Estructura de módulos)

**Purpose**: Crear el esqueleto de módulos backend y registrar los routers en la aplicación.

- [X] T001 Crear módulo `repse/sectors/` con `__init__.py`, `models.py`, `schemas.py`, `service.py` y `routes.py` (archivos vacíos) en `backend/src/repse/sectors/`
- [X] T002 Crear módulo `repse/giros/` con `__init__.py`, `models.py`, `schemas.py`, `service.py` y `routes.py` (archivos vacíos) en `backend/src/repse/giros/`
- [X] T003 Registrar `sectors_router` y `giros_router` con sus prefijos en `backend/src/repse/main.py`

---

## Phase 2: Foundational (Migración Alembic — BLOQUEANTE)

**Purpose**: Crear los cambios de esquema de BD que bloquean toda implementación de modelo.

**⚠️ CRÍTICO**: Ninguna historia de usuario puede comenzar hasta que esta migración exista y sea aplicable.

- [X] T004 Crear migración Alembic `0007_add_sectors_giros.py` en `backend/alembic/versions/` con: CREATE TABLE `sectors`, CREATE TABLE `giros`, ALTER TABLE `suppliers` (columnas `sector_id` y `giro_id` nullable + índices + FK RESTRICT según data-model.md)

**Checkpoint**: La migración existe y `alembic upgrade head` la aplica sin errores — trabajo de historias puede comenzar.

---

## Phase 3: User Story 1 — Gestionar catálogo de sectores (Priority: P1) 🎯 MVP

**Goal**: Administrador puede crear, editar y eliminar sectores desde la interfaz; el catálogo está disponible como dato de referencia global.

**Independent Test**: Crear un sector desde `/settings/catalogs/sectors`, editar su nombre, e intentar eliminarlo (primero sin dependencias → éxito; luego con giro asociado → error 409 con mensaje).

### Backend — US1

- [X] T005 [P] [US1] Implementar modelo `Sector` (id, name; sin TenantOwned; UniqueConstraint `uq_sectors_name`) en `backend/src/repse/sectors/models.py`
- [X] T006 [P] [US1] Implementar schemas `SectorIn` (name: str 2–120) y `SectorOut` (id, name) en `backend/src/repse/sectors/schemas.py`
- [X] T007 [US1] Implementar `SectorService` con métodos `list_all()`, `create()` (unicidad case-insensitive → 409), `update()` (unicidad → 409), `delete()` (deps giros → 409; deps suppliers → 409) en `backend/src/repse/sectors/service.py`
- [X] T008 [US1] Implementar endpoints `GET /sectors` (cualquier auth), `POST /sectors`, `PATCH /sectors/{id}`, `DELETE /sectors/{id}` (admin-only) según contrato en `backend/src/repse/sectors/routes.py`

### Frontend — US1

- [X] T009 [P] [US1] Crear `sectorsApi` con funciones `list()`, `create()`, `update()`, `remove()` que llaman a `/api/v1/sectors` en `frontend/src/lib/api/sectors.ts`
- [X] T010 [US1] Crear página `/settings/catalogs/sectors` con tabla de sectores + formulario inline crear/editar + confirmación de eliminación (manejo de error 409 "tiene dependencias") en `frontend/src/pages/settings/catalogs/sectors.tsx`
- [X] T011 [US1] Agregar enlace a "Sectores" en el hub de catálogos en `frontend/src/pages/settings/catalogs/index.tsx`
- [X] T012 [US1] Agregar ruta `/settings/catalogs/sectors` que carga `sectors.tsx` en `frontend/src/app/router.tsx`

**Checkpoint**: US1 completa — se pueden crear, editar y eliminar sectores; el catálogo es funcional de forma independiente.

---

## Phase 4: User Story 2 — Gestionar catálogo de giros (Priority: P1)

**Goal**: Administrador puede crear, editar y eliminar giros vinculados a un sector; el catálogo de giros funciona con selector de sector en cascada.

**Independent Test**: Crear un giro bajo un sector existente, verificar que solo aparece bajo ese sector al filtrar por `?sector_id`, editar el nombre, e intentar eliminar (sin proveedores → éxito; con proveedor asignado → error 409 con conteo).

### Backend — US2

- [X] T013 [P] [US2] Implementar modelo `Giro` (id, sector_id FK RESTRICT, name; UniqueConstraint `uq_giros_sector_name`) en `backend/src/repse/giros/models.py`
- [X] T014 [P] [US2] Implementar schemas `GiroIn` (sector_id, name: str 2–120), `GiroOut` (id, sector_id, sector_name, name) y `GiroBrief` (id, name) en `backend/src/repse/giros/schemas.py`
- [X] T015 [US2] Implementar `GiroService` con `list_all(sector_id=None)`, `create()` (verifica sector existe → 404; unicidad nombre dentro sector → 409), `update()` (valida sector destino + unicidad), `delete()` (proveedores asignados → 409 con conteo) en `backend/src/repse/giros/service.py`
- [X] T016 [US2] Implementar endpoints `GET /giros` (query param `?sector_id`; cualquier auth), `POST /giros`, `PATCH /giros/{id}`, `DELETE /giros/{id}` (admin-only) según contrato en `backend/src/repse/giros/routes.py`

### Frontend — US2

- [X] T017 [P] [US2] Crear `girosApi` con funciones `list(sectorId?)`, `create()`, `update()`, `remove()` que llaman a `/api/v1/giros` en `frontend/src/lib/api/giros.ts`
- [X] T018 [US2] Crear página `/settings/catalogs/giros` con selector de sector (para filtrar), tabla de giros filtrada por sector, formulario inline crear/editar (selector de sector + nombre), confirmación de eliminación (error 409 con mensaje de cuántos proveedores) en `frontend/src/pages/settings/catalogs/giros.tsx`
- [X] T019 [US2] Agregar enlace a "Giros" en el hub de catálogos en `frontend/src/pages/settings/catalogs/index.tsx`
- [X] T020 [US2] Agregar ruta `/settings/catalogs/giros` que carga `giros.tsx` en `frontend/src/app/router.tsx`

**Checkpoint**: US2 completa — se pueden crear giros bajo sectores, el catálogo sector→giro es funcional.

---

## Phase 5: User Story 3 — Asignar sector y giro a un proveedor (Priority: P2)

**Goal**: Al crear o editar un proveedor, el administrador puede asignar sector y giro (opcionales, en cascada). El proveedor ve su clasificación en solo lectura desde su portal.

**Independent Test**: Editar un proveedor existente, asignar sector y giro, guardar, verificar que aparecen en el perfil; luego entrar al portal del proveedor y confirmar que sector/giro son visibles y no editables.

### Backend — US3

- [X] T021 [US3] Extender modelo `Supplier` con columnas `sector_id` (nullable FK → sectors.id RESTRICT) y `giro_id` (nullable FK → giros.id RESTRICT) + relaciones ORM para eager load en `backend/src/repse/suppliers/models.py`
- [X] T022 [US3] Extender schemas `SupplierIn` y `SupplierPatch` con campos opcionales `sector_id: int | None` y `giro_id: int | None`; extender `SupplierListItem` y `SupplierDetailOut` con `sector: SectorOut | None` y `giro: GiroBrief | None` en `backend/src/repse/suppliers/schemas.py`
- [X] T023 [US3] Extender `SupplierService.create()` y `update()` con validaciones: `giro_id` sin `sector_id` → 422 `giro_requires_sector`; giro no pertenece al sector → 422 `giro_sector_mismatch`; cambio de `sector_id` sin nuevo `giro_id` limpia `giro_id` a NULL; agregar eager load de sector/giro en `list()` y `get()` en `backend/src/repse/suppliers/service.py`
- [X] T024 [US3] Actualizar endpoints `POST /suppliers` y `PATCH /suppliers/{id}` para aceptar y devolver `sector_id`/`giro_id` según contrato en `backend/src/repse/suppliers/routes.py`
- [X] T025 [US3] Extender `GET /portal/compliance` para incluir `sector: SectorOut | None` y `giro: GiroBrief | None` en la respuesta usando los datos del proveedor autenticado en `backend/src/repse/portal/routes.py`

### Frontend — US3

- [X] T026 [P] [US3] Agregar selectores sector y giro en cascada en formulario de nuevo proveedor: al cambiar sector se limpia giro y se filtra `girosApi.list(sectorId)`; si catálogo vacío los selectores aparecen deshabilitados con mensaje en `frontend/src/pages/suppliers/new.tsx`
- [X] T027 [P] [US3] Agregar selectores sector y giro en cascada en formulario de edición de proveedor (misma lógica que T026, pre-poblados con valores existentes) en `frontend/src/pages/suppliers/edit.tsx`
- [X] T028 [US3] Mostrar fila "Sector / Giro" (o "Sin clasificar") en la ficha de detalle del proveedor en `frontend/src/pages/suppliers/detail.tsx`
- [X] T029 [US3] Mostrar bloque sector/giro en modo solo lectura en el portal del proveedor (sin controles de edición) en `frontend/src/pages/portal/index.tsx`

**Checkpoint**: US3 completa — los proveedores pueden ser clasificados con sector/giro; la clasificación es visible en perfil y portal.

---

## Phase 6: User Story 4 — Filtrar proveedores por sector y giro (Priority: P3)

**Goal**: Cualquier usuario interno autenticado puede filtrar la lista de proveedores por sector y/o giro desde la toolbar.

**Independent Test**: Con al menos 3 proveedores clasificados en distintas combinaciones, aplicar filtro por sector → verificar que solo aparecen los correctos; agregar filtro de giro → lista se estrecha; sin resultados → mensaje "sin resultados".

### Backend — US4

- [X] T030 [US4] Agregar filtros opcionales `sector_id` y `giro_id` en `SupplierService.list()` (cláusulas WHERE adicionales después del filtro de tenant; índices `ix_suppliers_sector_id` e `ix_suppliers_giro_id` ya existen de la migración) en `backend/src/repse/suppliers/service.py`
- [X] T031 [US4] Exponer query params `?sector_id` y `?giro_id` en `GET /suppliers` en `backend/src/repse/suppliers/routes.py`

### Frontend — US4

- [X] T032 [US4] Agregar controles de filtro sector (select) y giro en cascada (select filtrado por sector) en la toolbar de la lista de proveedores; actualizar la query de TanStack Query con los params activos; mostrar mensaje "Sin resultados" cuando la lista esté vacía por filtro en `frontend/src/pages/suppliers/list.tsx`

**Checkpoint**: US4 completa — los usuarios internos pueden filtrar proveedores por sector y giro.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verificaciones de integridad y consistencia que cruzan múltiples historias.

- [X] T033 [P] Verificar que todas las respuestas de error 409 por dependencias en sectores/giros devuelven el formato estándar `{ "error": { "code": "...", "message": "..." } }` consistente con el contrato en `backend/src/repse/sectors/routes.py` y `backend/src/repse/giros/routes.py`
- [X] T034 [P] Verificar que `GET /suppliers` con filtros sector/giro respeta el aislamiento de tenant: un usuario de org A no puede ver proveedores de org B aunque ambos tengan el mismo `sector_id`
- [X] T035 Probar el flujo edge-case: proveedor con giro asignado → admin edita el giro moviéndolo a otro sector → proveedor retiene su `giro_id` original sin modificación automática (comportamiento documentado en data-model.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede iniciar de inmediato.
- **Foundational (Phase 2)**: Depende del Setup — **BLOQUEA todas las historias de usuario**.
- **US1 (Phase 3)** y **US2 (Phase 4)**: Dependen del Foundational; pueden ejecutarse en paralelo entre sí.
- **US3 (Phase 5)**: Depende de US1 y US2 completos (los modelos `Sector` y `Giro` deben existir para las FKs en `suppliers`).
- **US4 (Phase 6)**: Depende de US3 (el `service.py` de suppliers ya debe tener el eager load de sector/giro).
- **Polish (Phase 7)**: Depende de todas las historias completadas.

### User Story Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Migración) — BLOQUEANTE
    ├── US1 (Sectores) ─┐
    └── US2 (Giros)    ─┤ (paralelo)
                         ↓
                        US3 (Asignación proveedor + portal)
                         ↓
                        US4 (Filtrado lista)
                         ↓
                        Polish
```

### Within Each User Story

- Modelo(s) → Schemas → Service → Routes (backend)
- API client → Página/componente → Router (frontend)
- Backend y frontend de la misma historia pueden avanzar en paralelo una vez que el contrato API está claro

### Parallel Opportunities

- T001 y T002 (Phase 1) en paralelo.
- T005 y T006 (modelo + schemas de sectores) en paralelo.
- T013 y T014 (modelo + schemas de giros) en paralelo.
- T009 (sectorsApi) en paralelo con T008 (routes sectors).
- T017 (girosApi) en paralelo con T016 (routes giros).
- T026 y T027 (formularios new/edit supplier) en paralelo.
- T033 y T034 (polish) en paralelo.

---

## Parallel Example: User Story 1

```bash
# Backend — lanzar en paralelo:
Task T005: Modelo Sector en backend/src/repse/sectors/models.py
Task T006: Schemas SectorIn/SectorOut en backend/src/repse/sectors/schemas.py

# Luego, en secuencia:
Task T007: SectorService (depende de T005, T006)
Task T008: Routes /sectors (depende de T007)

# Frontend — puede avanzar en paralelo al backend:
Task T009: sectorsApi en frontend/src/lib/api/sectors.ts
Task T010: Página sectors.tsx (depende de T009)
Task T011: Hub de catálogos (paralelo con T010)
Task T012: Router (paralelo con T010)
```

---

## Implementation Strategy

### MVP First (User Stories 1 y 2)

1. Completar Phase 1 (Setup) y Phase 2 (Migración)
2. Completar Phase 3 (US1 — Sectores) → **VALIDAR independientemente**
3. Completar Phase 4 (US2 — Giros) → **VALIDAR independientemente**
4. **DETENER y DEMOSTRAR**: catálogos de referencia funcionales
5. Continuar con US3 (asignación) y US4 (filtrado)

### Incremental Delivery

1. Setup + Migración → Base de datos lista
2. US1 → Catálogo de sectores funcional (admin puede crear/editar/eliminar)
3. US2 → Catálogo de giros funcional (vinculado a sectores)
4. US3 → Proveedores clasificables, portal muestra clasificación
5. US4 → Filtrado habilitado en lista de proveedores
6. Polish → Verificaciones de integridad cruzada

### Parallel Team Strategy (si hay varios desarrolladores)

1. Dev A: Phase 1 + Phase 2 (Setup + Migración) — todos esperan
2. Una vez completado Phase 2:
   - Dev A: US1 (Sectores — backend + frontend)
   - Dev B: US2 (Giros — backend + frontend)
3. Ambos completan → Dev A+B: US3 juntos (backend un dev, frontend el otro)
4. US4 (pequeña) → cualquier dev disponible
5. Polish → revisión conjunta

---

## Notes

- **[P]** = archivos distintos, sin dependencias entre sí → ejecutar en paralelo
- **[Story]** = etiqueta de historia de usuario para trazabilidad
- Cada historia es independientemente completable y verificable
- La migración T004 es el único bloqueante real antes de cualquier implementación de modelo
- Los campos `sector_id`/`giro_id` en `suppliers` son nullable: compatibilidad total con datos existentes sin migración de datos
- Hard delete exclusivo — sin soft-delete ni `is_active`
- Los catálogos `sectors`/`giros` son globales (sin `organization_id`): excepción justificada al Principio II de la constitución (ver research.md Decisión 1)
