---
description: "Task list for 003-document-catalog-admin (catalog administration: document types + supplier types + requirements)"
---

# Tasks: Administración de Catálogos (Documentos + Proveedores)

**Input**: Design documents from `/specs/003-document-catalog-admin/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: La constitución exige test-first para rutas críticas (aislamiento multi-tenant, "Sin clasificar" inmutable, recálculo de cumplimiento, optimistic concurrency). Esos tests se incluyen como **obligatorios**.

**Organization**: Tareas agrupadas por user story. 4 user stories (US1+US3+US4 son P1, US2 es P2). El wizard de plantillas se removió del scope el 2026-05-17.

**Asume que el 001 ya está implementado** — entidades `DocumentType`, `SupplierType`, `SupplierTypeDocumentRequirement`, `TenantDocumentTypeSetting`, mixin `TenantOwned`, módulos `document_types/`, `supplier_types/`, recálculo de cumplimiento, audit log y CLAUDE conventions ya existen. Este tasks.md solo agrega las capacidades de administración.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: paralelizable (archivo distinto, sin dependencias).
- **[Story]**: US1, US2, US3 o US4 cuando aplica.
- Rutas exactas en la descripción.

## Path Conventions

Monorepo del 001: `backend/` (FastAPI + SQLAlchemy) y `frontend/` (Vite + React + Tailwind). Este spec extiende `document_types/` y `supplier_types/` del backend y agrega una sección "Configuración → Catálogos" al frontend.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: agregar a la app del 001 las piezas transversales que este spec necesita pero no son específicas de una US.

- [ ] T001 [P] Crear módulo `catalog_changes/` en el backend con [backend/src/repse/catalog_changes/__init__.py](backend/src/repse/catalog_changes/__init__.py), un placeholder de `notifier.py` que se completa en Foundational.
- [ ] T002 [P] Agregar feature flag `CATALOG_ADMIN_ENABLED` en [backend/src/repse/config.py](backend/src/repse/config.py) (default `true`) para deshabilitar la sección durante despliegues si fuera necesario.
- [ ] T003 [P] Crear ruta del frontend `/settings/catalogs` en [frontend/src/app/router.tsx](frontend/src/app/router.tsx) con redirect a `document-types` por defecto.

**Checkpoint**: la sección "Catálogos" responde 404 o 200 placeholder; el resto del setup ya viene del 001.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: utilidades transversales a las 4 user stories. Sin esto, el resto rompe el principle de la constitución de optimistic concurrency y observabilidad.

**⚠️ CRITICAL**: ninguna user story puede empezar hasta cerrar esta fase.

- [ ] T004 Implementar dependencia FastAPI `if_match(request)` en [backend/src/repse/common/if_match.py](backend/src/repse/common/if_match.py) que valida el header `If-Match: "<updated_at ISO>"` contra el `updated_at` actual del recurso; si no coincide responde `409 stale_update` con el cuerpo actual. Aplica a `DocumentType`, `SupplierType`, `SupplierTypeDocumentRequirement` (research.md §4).
- [ ] T005 Implementar `catalog_changes/notifier.py` (función `notify_canonical_doc_type_added(new_doc_type_slug, name)`) en [backend/src/repse/catalog_changes/notifier.py](backend/src/repse/catalog_changes/notifier.py) que crea una entrada en `notifications` para cada admin de cada tenant (research.md §1). Si el módulo `alerts/` del spec 002 no está mergeado, inserta en una tabla `system_notifications` temporal.
- [ ] T006 [P] Asegurar que `documents/recalculator.py` (del 001) expone `recalc_for_supplier_type(organization_id, supplier_type_id)` y `recalc_for_document_type(organization_id, document_type_id)` como funciones públicas en [backend/src/repse/documents/recalculator.py](backend/src/repse/documents/recalculator.py).
- [ ] T007 [P] Implementar helper de bitácora `audit.write_catalog_event(actor, action, entity_type, entity_id, prev, new)` en [backend/src/repse/audit/service.py](backend/src/repse/audit/service.py) que reusa el AuditLog del 001 con un schema consistente para los eventos del catálogo.
- [ ] T008 [P] Agregar al frontend el hook `useOptimisticConcurrency(resource)` en [frontend/src/lib/optimistic.ts](frontend/src/lib/optimistic.ts) que: (a) toma el `updated_at` del GET previo, (b) lo emite como header `If-Match` en el siguiente PATCH/DELETE, (c) ante `409 stale_update` re-fetcha y muestra un modal "Otra persona modificó este registro. ¿Refrescar?".
- [ ] T009 [P] Crear página de hub `frontend/src/pages/settings/catalogs/index.tsx` con dos pestañas: "Tipos de documento", "Tipos de proveedor". Cada pestaña carga su propia ruta hija. Solo visible para `role='admin'` (FR-001).
- [ ] T010 [P] Crear `frontend/src/components/catalogs/PeriodicitySelect.tsx` que soporta valores `monthly|bimonthly|annual|none` + opción especial "Heredar" (envía NULL al backend) para los selects de periodicidad efectiva.

**Checkpoint**: el header `If-Match` se valida en todas las mutaciones; los hooks frontend manejan el 409; los notifiers están listos para emitir cuando aparezcan canónicos nuevos.

---

## Phase 3: User Story 1 — Activar y desactivar tipos del catálogo canónico de DOCUMENTOS (Priority: P1) 🎯 MVP

**Goal**: un administrador puede activar/desactivar tipos canónicos del catálogo dentro de su tenant. Los cambios disparan recálculo de cumplimiento y se registran en bitácora. El cambio nunca afecta a otros tenants.

**Independent Test**: con dos tenants A y B, desactivar `ICSOE` en A; verificar (a) `GET /api/v1/document-types?include_inactive=false` en A no incluye ICSOE, en B sí; (b) los proveedores de A dejan de exigir ICSOE; (c) bitácora del tenant A registra la desactivación.

### Tests obligatorios

- [ ] T011 [P] [US1] Contract test: `POST /api/v1/document-types/{id}/archive` para un canónico crea/actualiza la fila correspondiente en `tenant_document_type_settings` (active=false) y responde 200 con el estado actualizado, en [backend/tests/contract/test_document_types_archive_canonical.py](backend/tests/contract/test_document_types_archive_canonical.py).
- [ ] T012 [P] [US1] Integration test multi-tenant negativo: tenant A desactiva ICSOE; tenant B sigue viéndolo activo + sus proveedores siguen exigiéndolo, en [backend/tests/integration/test_catalog_isolation_us1.py](backend/tests/integration/test_catalog_isolation_us1.py).
- [ ] T013 [P] [US1] Integration test: tras desactivar un tipo con documentos cargados, los documentos se conservan en el detalle del proveedor etiquetados "tipo desactivado" y NO cuentan como faltante, en [backend/tests/integration/test_archive_preserves_history.py](backend/tests/integration/test_archive_preserves_history.py).
- [ ] T014 [P] [US1] Integration test: reactivar un tipo previamente desactivado reincorpora los documentos al cálculo de estado, en [backend/tests/integration/test_restore_recalculates.py](backend/tests/integration/test_restore_recalculates.py).
- [ ] T015 [P] [US1] Integration test: optimistic concurrency — dos PATCH simultáneos sobre el mismo `tenant_document_type_settings`, el segundo recibe `409 stale_update`, en [backend/tests/integration/test_optimistic_concurrency_settings.py](backend/tests/integration/test_optimistic_concurrency_settings.py).

### Service + Routes (backend)

- [ ] T016 [US1] Servicio `document_types.activate_canonical(org_id, doc_type_id, actor)` y `deactivate_canonical(org_id, doc_type_id, reason, actor)` en [backend/src/repse/document_types/service.py](backend/src/repse/document_types/service.py). Cada uno: (a) valida que el tipo sea `origin='canonical'`, (b) crea/actualiza la fila de `tenant_document_type_settings`, (c) llama a `recalc_for_document_type`, (d) escribe audit log.
- [ ] T017 [US1] Endpoint `POST /api/v1/document-types/{id}/archive` y `POST /api/v1/document-types/{id}/restore` (rutas únicas para canónicos y personalizados — el servicio decide qué hacer según `origin`) en [backend/src/repse/document_types/routes.py](backend/src/repse/document_types/routes.py).
- [ ] T018 [US1] Endpoint `GET /api/v1/document-types/canonical-updates` que lista canónicos cuyo `created_at` es posterior al `provisioning_at` del tenant y que están actualmente desactivados en él, en [backend/src/repse/document_types/routes.py](backend/src/repse/document_types/routes.py).
- [ ] T019 [US1] Trigger en migrations Alembic: cuando una migration `0XXX_add_canonical_*.py` agrega un `DocumentType` canónico nuevo, llamar `notify_canonical_doc_type_added` (T005) en su `upgrade()`. Documentar el patrón en [backend/alembic/README.md](backend/alembic/README.md).

### Frontend US1

- [ ] T020 [P] [US1] Hook + queries Tanstack para `documentTypes`, `archiveDocumentType`, `restoreDocumentType`, `canonicalUpdates` en [frontend/src/lib/api/document-types.ts](frontend/src/lib/api/document-types.ts).
- [ ] T021 [P] [US1] Página listado de tipos de documento `frontend/src/pages/settings/catalogs/document-types.tsx`: tabla con columnas "Nombre", "Origen", "Periodicidad", "Estado", "Acciones". Filtros: solo activos / todos. Botón "Activar/Desactivar" para canónicos.
- [ ] T022 [P] [US1] Componente `<CanonicalUpdatesBadge>` en el header de la página que consulta `/document-types/canonical-updates` y muestra un dot rojo con el conteo. Click abre un drawer con la lista para activar rápido.
- [ ] T023 [P] [US1] E2E Playwright: admin desactiva ICSOE; verifica que desaparece del selector al asignar requisitos; reactiva; reaparece. En [frontend/tests/e2e/us1_catalog_admin.spec.ts](frontend/tests/e2e/us1_catalog_admin.spec.ts).

**Checkpoint**: US1 funcional. El admin puede tomar el catálogo canónico de su tenant y filtrarlo a lo que realmente aplica.

---

## Phase 4: User Story 2 — Crear y mantener tipos personalizados de DOCUMENTO (Priority: P2)

**Goal**: un administrador puede crear, editar, archivar y eliminar tipos de documento personalizados (`origin='custom'`) propios de su tenant.

**Independent Test**: tenant A crea el tipo "Constancia interna" con periodicidad bimestral; tenant B no lo ve. Intentar eliminar el tipo personalizado mientras existe un documento cargado contra él retorna 409 con `has_dependencies`. Archivar funciona; los documentos cargados se conservan en histórico.

### Tests obligatorios

- [ ] T024 [P] [US2] Contract test: `POST /api/v1/document-types` valida nombre único por tenant (case-insensitive), rechaza periodicidad inválida, retorna 201 con `origin='custom'`, en [backend/tests/contract/test_document_types_create_custom.py](backend/tests/contract/test_document_types_create_custom.py).
- [ ] T025 [P] [US2] Contract test: `DELETE /api/v1/document-types/{id}` rechaza con `409 has_dependencies` cuando hay documentos cargados o asociaciones con `SupplierType`, en [backend/tests/contract/test_document_types_delete_guard.py](backend/tests/contract/test_document_types_delete_guard.py).
- [ ] T026 [P] [US2] Integration test: editar la periodicidad de un tipo personalizado solo aplica a cargas posteriores; los documentos previos conservan su periodicidad efectiva original (FR-006), en [backend/tests/integration/test_custom_periodicity_change.py](backend/tests/integration/test_custom_periodicity_change.py).
- [ ] T027 [P] [US2] Integration test: nombres duplicados (insensibles a mayúsculas y espacios) entre canónico + custom son rechazados con `409 name_exists`, en [backend/tests/integration/test_document_type_name_uniqueness.py](backend/tests/integration/test_document_type_name_uniqueness.py).

### Service + Routes (backend)

- [ ] T028 [US2] Servicio `document_types.create_custom(org_id, name, periodicity, description, actor)` y `update_custom`, `delete_custom`, `archive_custom`, `restore_custom` en [backend/src/repse/document_types/service.py](backend/src/repse/document_types/service.py). Validan: unicidad de nombre por tenant, `origin='custom'` en cualquier mutación, dependencias en delete, audit log + recálculo en cada paso.
- [ ] T029 [US2] Endpoint `POST /api/v1/document-types` en [backend/src/repse/document_types/routes.py](backend/src/repse/document_types/routes.py).
- [ ] T030 [US2] Endpoint `PATCH /api/v1/document-types/{id}` (admin only, valida `origin='custom'`, exige `If-Match`) en [backend/src/repse/document_types/routes.py](backend/src/repse/document_types/routes.py).
- [ ] T031 [US2] Endpoint `DELETE /api/v1/document-types/{id}` (admin only, exige `If-Match`, rechaza con `409 has_dependencies` si aplica) en [backend/src/repse/document_types/routes.py](backend/src/repse/document_types/routes.py).

### Frontend US2

- [ ] T032 [P] [US2] Componente `frontend/src/components/catalogs/DocumentTypeForm.tsx` con campos nombre + periodicidad + descripción y validación zod. Reusa `<PeriodicitySelect>` (T010) sin opción "Heredar" (los DocumentType no heredan).
- [ ] T033 [P] [US2] Página listado (extendida del T021): agregar botones "Nuevo tipo personalizado", "Editar" (solo para custom), "Eliminar/Archivar" según dependencias. Modal de eliminación con opción "Archivar en su lugar" cuando responde 409.
- [ ] T034 [P] [US2] E2E Playwright: admin crea "Constancia interna" bimestral, lo asigna a un `SupplierType` existente, intenta eliminarlo (esperado 409), lo archiva exitosamente. En [frontend/tests/e2e/us2_custom_document_type.spec.ts](frontend/tests/e2e/us2_custom_document_type.spec.ts).

**Checkpoint**: US1 + US2 cubren completo el catálogo de tipos de documento.

---

## Phase 5: User Story 3 — Administrar el catálogo de TIPOS DE PROVEEDOR (Priority: P1)

**Goal**: un administrador puede crear, editar, archivar, restaurar y eliminar tipos de proveedor personalizados. "Sin clasificar" (`origin='system'`) es inmutable.

**Independent Test**: con dos tenants A y B, crear "Construcción" en A; verificar que aparece como opción al crear proveedores en A y NO aparece en B. Intentar archivar "Sin clasificar" en cualquier tenant retorna 403. Archivar "Construcción" con 3 proveedores asignados retorna 200 + `affected_suppliers_count=3` y los proveedores quedan marcados "tipo archivado, reclasificar".

### Tests obligatorios

- [ ] T035 [P] [US3] Contract test: `POST /api/v1/supplier-types` rechaza nombres duplicados por tenant, retorna 201 con `origin='custom'`, en [backend/tests/contract/test_supplier_types_create.py](backend/tests/contract/test_supplier_types_create.py).
- [ ] T036 [P] [US3] Integration test crítico: cualquier intento de PATCH/archive/restore/DELETE sobre el `SupplierType` con `origin='system'` ("Sin clasificar") retorna `403 system_type_immutable`, en [backend/tests/integration/test_system_supplier_type_immutable.py](backend/tests/integration/test_system_supplier_type_immutable.py).
- [ ] T037 [P] [US3] Integration test: archivar un `SupplierType` con proveedores asignados retorna 200 + `affected_suppliers_count`; los proveedores se siguen consultando pero no cuentan al agregado del tenant hasta reclasificarlos, en [backend/tests/integration/test_archive_supplier_type_with_suppliers.py](backend/tests/integration/test_archive_supplier_type_with_suppliers.py).
- [ ] T038 [P] [US3] Integration test multi-tenant: tenant A crea "Construcción"; consulta desde tenant B con el mismo `id` responde 404, en [backend/tests/integration/test_supplier_types_isolation.py](backend/tests/integration/test_supplier_types_isolation.py).

### Service + Routes (backend)

- [ ] T039 [US3] Servicio `supplier_types.create(org_id, name, description, actor)` con validación de unicidad de nombre por tenant (case-insensitive) en [backend/src/repse/supplier_types/service.py](backend/src/repse/supplier_types/service.py).
- [ ] T040 [US3] Servicios `supplier_types.update`, `archive`, `restore`, `delete` en [backend/src/repse/supplier_types/service.py](backend/src/repse/supplier_types/service.py). Todos: (a) rechazan si `origin='system'`, (b) audit log, (c) `archive` dispara recálculo del tenant y devuelve `affected_suppliers_count`, (d) `delete` rechaza si hay proveedores o requisitos.
- [ ] T041 [US3] Endpoint `POST /api/v1/supplier-types` en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).
- [ ] T042 [US3] Endpoint `PATCH /api/v1/supplier-types/{id}` (admin only, exige `If-Match`) en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).
- [ ] T043 [US3] Endpoints `POST /api/v1/supplier-types/{id}/archive` y `POST /api/v1/supplier-types/{id}/restore` en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).
- [ ] T044 [US3] Endpoint `DELETE /api/v1/supplier-types/{id}` (exige `If-Match`, retorna `409 has_dependencies` si aplica) en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).

### Frontend US3

- [ ] T045 [P] [US3] Hook + queries Tanstack para `supplierTypes`, `createSupplierType`, `updateSupplierType`, `archiveSupplierType`, `restoreSupplierType`, `deleteSupplierType` en [frontend/src/lib/api/supplier-types.ts](frontend/src/lib/api/supplier-types.ts).
- [ ] T046 [P] [US3] Componente `frontend/src/components/catalogs/SupplierTypeForm.tsx` con nombre + descripción + validación zod.
- [ ] T047 [P] [US3] Página listado `frontend/src/pages/settings/catalogs/supplier-types.tsx`: tabla con "Nombre", "Origen", "Estado", "# proveedores", "# requisitos", "Acciones". Acciones deshabilitadas con tooltip cuando `origin='system'`.
- [ ] T048 [P] [US3] Modal "Archivar tipo de proveedor" que: (a) si tiene proveedores muestra warning "Los X proveedores quedarán marcados como 'tipo archivado, reclasificar'", (b) deja confirmar igualmente, (c) muestra link "Ver lista de proveedores afectados" hacia el listado filtrado.
- [ ] T049 [P] [US3] E2E Playwright: admin crea "Construcción"; intenta archivar "Sin clasificar" (esperado 403/UI deshabilitada); archiva "Construcción" con 1 proveedor asociado; verifica que el proveedor queda con etiqueta "tipo archivado". En [frontend/tests/e2e/us3_supplier_types_admin.spec.ts](frontend/tests/e2e/us3_supplier_types_admin.spec.ts).

**Checkpoint**: US3 funcional. El catálogo de tipos de proveedor es administrable.

---

## Phase 6: User Story 4 — Definir requisitos por tipo de proveedor (Priority: P1)

**Goal**: desde el detalle de un `SupplierType`, un administrador puede agregar/quitar `DocumentType` como requisitos y sobrescribir su periodicidad. Editar requisitos dispara recálculo asíncrono del cumplimiento de los proveedores afectados.

**Independent Test**: en "Construcción" agregar 6 requisitos (incluyendo `SAT` con periodicidad heredada y `SAT` luego sobrescrita a bimestral); crear un proveedor de tipo "Construcción"; verificar que su detalle muestra exactamente esos 6 documentos como requeridos con la periodicidad efectiva correcta; cambiar el override y verificar que el detalle del proveedor refleja el cambio tras el recálculo (<60 s).

### Tests obligatorios

- [ ] T050 [P] [US4] Contract test: `POST /api/v1/supplier-types/{id}/requirements` rechaza con `409 doc_type_inactive` cuando el `DocumentType` está desactivado en el tenant, en [backend/tests/contract/test_requirements_create_guard.py](backend/tests/contract/test_requirements_create_guard.py).
- [ ] T051 [P] [US4] Contract test: `PATCH /api/v1/supplier-type-requirements/{id}` con `periodicity_override='bimonthly'` actualiza la periodicidad efectiva; `null` regresa a herencia del `DocumentType`. Side effect: audit log con prev/new, en [backend/tests/contract/test_requirements_periodicity_override.py](backend/tests/contract/test_requirements_periodicity_override.py).
- [ ] T052 [P] [US4] Integration test: agregar un requisito a un `SupplierType` que tiene proveedores causa que los proveedores pasen a exigir ese documento (status="Faltante" hasta que se cargue), validado en el detalle del proveedor dentro de 60s, en [backend/tests/integration/test_requirements_recalculation.py](backend/tests/integration/test_requirements_recalculation.py).
- [ ] T053 [P] [US4] Integration test: retirar un requisito (`DELETE`) no borra los documentos cargados sobre él; quedan en histórico marcados "requisito retirado", en [backend/tests/integration/test_requirement_retired_history.py](backend/tests/integration/test_requirement_retired_history.py).
- [ ] T054 [P] [US4] Integration test: cambiar `periodicity_override` reevalúa los documentos previamente cargados con la nueva periodicidad efectiva (cambio de estado vigente↔vencido si aplica), en [backend/tests/integration/test_periodicity_override_reevaluates.py](backend/tests/integration/test_periodicity_override_reevaluates.py).

### Service + Routes (backend)

- [ ] T055 [US4] Servicio `supplier_types.create_requirement(org_id, supplier_type_id, doc_type_id, periodicity_override, actor)` con validaciones: tipo doc activo, par único (`supplier_type_id`, `doc_type_id`) sin requisito ya activo. Dispara `recalc_for_supplier_type`. En [backend/src/repse/supplier_types/service.py](backend/src/repse/supplier_types/service.py).
- [ ] T056 [US4] Servicios `update_requirement_periodicity`, `retire_requirement`, `restore_requirement` en [backend/src/repse/supplier_types/service.py](backend/src/repse/supplier_types/service.py). Todos audit log + recálculo.
- [ ] T057 [US4] Endpoint `POST /api/v1/supplier-types/{type_id}/requirements` en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).
- [ ] T058 [US4] Endpoint `PATCH /api/v1/supplier-type-requirements/{req_id}` (admin only, exige `If-Match`) en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).
- [ ] T059 [US4] Endpoint `DELETE /api/v1/supplier-type-requirements/{req_id}` (admin only, marca `status='retired'`, exige `If-Match`) en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).
- [ ] T060 [US4] Endpoint `POST /api/v1/supplier-type-requirements/{req_id}/restore` que verifica que el `DocumentType` siga activo; si no, retorna `409 doc_type_inactive`. En [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).

### Frontend US4

- [ ] T061 [P] [US4] Hook + queries Tanstack para `requirements` (`getByType`, `create`, `update`, `retire`, `restore`) en [frontend/src/lib/api/requirements.ts](frontend/src/lib/api/requirements.ts).
- [ ] T062 [P] [US4] Página detalle del `SupplierType` `frontend/src/pages/settings/catalogs/supplier-type-detail.tsx`: header con nombre/descripción + botón editar; tabla de requisitos con columnas "Tipo de documento", "Periodicidad efectiva", "Override", "Estado", "Acciones".
- [ ] T063 [P] [US4] Componente `frontend/src/components/catalogs/RequirementRow.tsx` que renderiza una fila editable in-place: select de `DocumentType` (al agregar), `<PeriodicitySelect>` con "Heredar" como default, botón retirar/restaurar.
- [ ] T064 [P] [US4] Modal "Agregar requisito" con `<DocumentTypeSelect>` filtrando solo tipos activos del tenant. Si el usuario elige uno inactivo (no debería ser posible por el filtro, pero por si acaso), muestra link directo a reactivarlo desde la sección de tipos de documento.
- [ ] T065 [P] [US4] E2E Playwright: en "Construcción", agregar 4 requisitos; sobrescribir periodicidad de uno; retirar otro; crear un proveedor "Construcción" y verificar que su detalle muestra los 3 requisitos vigentes con la periodicidad correcta. En [frontend/tests/e2e/us4_requirements.spec.ts](frontend/tests/e2e/us4_requirements.spec.ts).

**Checkpoint**: las 4 user stories cierran. El admin tiene control completo sobre qué documenta exige a cada industria de proveedor.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: hardening específico de 003.

- [ ] T066 [P] Test unitario que verifica que ningún endpoint del 003 acepta requests SIN sesión (401) y que todos los admin-only retornan 403 para viewer/manager, en [backend/tests/unit/test_003_authz_matrix.py](backend/tests/unit/test_003_authz_matrix.py).
- [ ] T067 [P] Test de carga: tenant con 500 proveedores asignados a un `SupplierType`. Cambiar `periodicity_override` de uno de sus requisitos. El recálculo asíncrono completa en <60s (SC verificado). En [backend/tests/performance/test_recalc_supplier_type_500.py](backend/tests/performance/test_recalc_supplier_type_500.py).
- [ ] T068 [P] Validar contra los contratos: generar OpenAPI desde FastAPI y comparar contra los `.md` de [contracts/](./contracts/) con un script de diff. Falla CI si hay drift. En [backend/tests/contract/test_openapi_matches_003.py](backend/tests/contract/test_openapi_matches_003.py).
- [ ] T069 [P] Componente de error para `409 stale_update` en frontend: modal claro "Otra persona modificó este registro mientras lo editabas. Refrescar mostrará la versión actual y perderá tus cambios." con botones "Refrescar" y "Cancelar". Probado por un test en [frontend/tests/unit/StaleUpdateModal.test.tsx](frontend/tests/unit/StaleUpdateModal.test.tsx).
- [ ] T070 Smoke manual completo siguiendo [quickstart.md](./quickstart.md#smoke-test-us1--us4-del-spec) con tenant fresco; documentar evidencia en [docs/smoke-003-YYYY-MM-DD.md](docs/smoke-003-YYYY-MM-DD.md).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: depende del 001 ya implementado.
- **Phase 2 (Foundational)**: depende de Phase 1. Bloquea US1-US4.
- **Phase 3 (US1, P1)**: depende de Phase 2.
- **Phase 4 (US2, P2)**: depende de Phase 2. Comparte rutas con US1 (`document_types/routes.py`) pero tareas son sobre archivos distintos en su mayoría; conviene cerrar US1 primero para evitar conflictos de merge.
- **Phase 5 (US3, P1)**: depende de Phase 2; independiente de US1/US2.
- **Phase 6 (US4, P1)**: depende de Phase 5 (necesita `SupplierType` existente) y de Phase 3 (necesita `DocumentType` activo para asociar). Empieza tras US3 y US1 cerradas.
- **Phase 7 (Polish)**: depende de las 4 US.

### Critical-path sequencing dentro de US3 + US4

- T039 (servicio create supplier_type) → T041 (endpoint POST) → T045/T046/T047 (frontend) → US4 puede empezar.
- T055 (servicio create requirement) → T057 (endpoint) → T061/T063 (frontend) → US4 cerrada.

### Parallel Opportunities

- **Phase 2 Foundational**: T006/T007/T008/T009/T010 todos paralelos.
- **Phase 3 US1**: tests T011–T015 paralelos. Frontend T020/T021/T022/T023 paralelos.
- **Phase 4 US2**: tests T024–T027 paralelos. Frontend T032/T033/T034 paralelos.
- **Phase 5 US3**: tests T035–T038 paralelos. Frontend T045–T049 paralelos.
- **Phase 6 US4**: tests T050–T054 paralelos. Frontend T061–T065 paralelos.
- **Phase 7 Polish**: T066–T069 paralelos.

### Equipo paralelo (si aplica)

Con 2 desarrolladores, tras Phase 2:
- Dev A: US1 + US2 (catálogo de documentos).
- Dev B: US3 (catálogo de tipos de proveedor).
- Ambos convergen en US4 (requiere ambas listas implementadas).

---

## Parallel Example: arranque de US3

```bash
# Tras Phase 2 cerrada, lanza los 4 tests críticos en paralelo:
Task: "T035 [US3] Contract test create supplier_type"
Task: "T036 [US3] Integration test system_type immutable"
Task: "T037 [US3] Integration test archive with suppliers"
Task: "T038 [US3] Integration test isolation"

# En paralelo, los 5 archivos de frontend:
Task: "T045 Hook + queries supplier-types"
Task: "T046 SupplierTypeForm"
Task: "T047 Página listado supplier-types"
Task: "T048 Modal archivar"
Task: "T049 E2E"
```

---

## Implementation Strategy

### MVP (US1 + US3)

1. Phase 1 (Setup): T001–T003.
2. Phase 2 (Foundational): T004–T010.
3. Phase 3 (US1): T011–T023.
4. Phase 5 (US3): T035–T049.
5. Validar contra [quickstart.md](./quickstart.md): admin desactiva canónico + admin crea tipo de proveedor con "Sin clasificar" como fallback intacto.
6. Deploy / demo si pasa.

US2 + US4 agregan capacidades pero los dos P1 listados arriba ya entregan valor mensurable (catálogo recortado + clasificación de proveedores).

### Incremental delivery

1. Setup + Foundational → infra lista.
2. US1 → admin reduce ruido del catálogo. **Deploy / demo**.
3. US3 → admin clasifica industrias. **Deploy / demo**.
4. US4 → requisitos por industria. **Deploy / demo** (cierra el valor principal del spec).
5. US2 → tipos de documento personalizados (deseable, no bloqueante).
6. Polish.

---

## Notes

- [P] = paralelizable (archivo distinto, sin dependencias inmediatas).
- [Story] mapea a US1 / US2 / US3 / US4 del [spec.md](./spec.md).
- Tests obligatorios cubren rutas críticas (multi-tenant, system_type immutable, recálculo, optimistic concurrency). Otros tests son opcionales.
- Verificar tests fallando antes de implementar (rojo → verde → refactor).
- Commitear tras cada task o grupo coherente; commit message referencia el `TID`.
- Pausar en cada Checkpoint para validar.
- **Wizard de plantillas**: fuera de scope (2026-05-17). NO implementar `templates.py`, `TemplateImportWizard.tsx` ni los endpoints `/supplier-type-templates`. Si surge la demanda, será un spec dedicado.
