# Tasks: Portal del Proveedor — Visor de Documentación

**Input**: Design documents from `specs/009-proveedor-portal-viewer/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅

**Tests**: Se incluyen los tests de autenticación, aislamiento de tenant, upload y submit porque son **obligatorios** según el Principio III de la Constitución (caminos críticos deben tener pruebas antes del merge).

**Organization**: Tareas agrupadas por historia de usuario del spec para permitir implementación y prueba independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece la tarea (US1–US6 según spec.md)

---

## Phase 1: Setup (Infraestructura compartida)

**Purpose**: Crear la estructura del nuevo paquete `portal` en el backend.

- [X] T001 Crear directorio `backend/src/repse/portal/` (paquete Python vacío)

---

## Phase 2: Foundational Part 1 — Auth y modelos de usuarios (Prerrequisitos bloqueantes)

**Purpose**: Cambios en BD y en la capa de sesión que bloquean TODAS las historias de usuario.

**⚠️ CRÍTICO**: Ninguna historia puede comenzar hasta que esta fase esté completa.

- [X] T002 Crear migración `backend/alembic/versions/0005_add_supplier_role_and_user_supplier_link.py` — upgrade: ALTER TABLE users MODIFY role ENUM añadiendo 'supplier'; ADD COLUMN supplier_id BIGINT NULL FK → suppliers.id ON DELETE SET NULL; CREATE INDEX ix_users_supplier
- [X] T003 [P] Extender `backend/src/repse/users/models.py` — agregar `SUPPLIER = "supplier"` al enum `Role`; agregar campo `supplier_id: Mapped[int | None]` con FK a `suppliers.id` ON DELETE SET NULL e index=True
- [X] T004 [P] Extender `backend/src/repse/auth/session.py` — agregar `supplier_id: int | None = None` a `SessionPayload`; actualizar `issue()` para incluir `"supplier_id": payload.supplier_id`; actualizar `read()` usando `.get("supplier_id")` (backward-compatible con cookies antiguas)

**Checkpoint**: Migración 0005 lista y modelos actualizados — pueden comenzar todas las historias.

---

## Phase 2B: Foundational Part 2 — Modelos y migración de US5/US6 (Prerrequisitos para US5 y US6)

**Purpose**: Crear la tabla `portal_submissions`, el modelo SQLAlchemy y los schemas Pydantic necesarios para las fases de carga y envío a validación.

**⚠️ CRÍTICO**: Las fases US5 y US6 no pueden comenzar hasta que esta sección esté completa.

- [X] T026 Crear migración `backend/alembic/versions/0006_add_portal_submissions.py` — CREATE TABLE portal_submissions con todos los campos del data-model.md (organization_id, supplier_id, document_type_id, coverage_period_start, submitted_at, submitted_by, status ENUM, rejection_reason, pre_submission_status ENUM, created_at, updated_at) e índice compuesto `idx_portal_submissions_lookup`
- [X] T027 [P] Crear modelo SQLAlchemy `PortalSubmission` en `backend/src/repse/portal/models.py` — mapear todos los campos de `portal_submissions` incluyendo FKs a organizations, suppliers, document_types y users
- [X] T028 [P] Crear schemas Pydantic del portal en `backend/src/repse/portal/schemas.py` — definir `SubmissionOut` (submission_id, supplier_id, document_type_id, coverage_period_start, submitted_at, status), `UploadOut` (id, document_type_id, coverage_period_start, coverage_period_end, status, file_name_original, file_size_bytes, version, created_at) y `SubmitRequest` (coverage_period_start: date | None)
- [X] T029 Actualizar `backend/src/repse/compliance/service.py` — en `get_annual_compliance()` agregar query a `portal_submissions` para obtener celdas con `status='pending'`; retornar `CellStatus.SUBMITTED` para esas celdas (Decision 10 del research.md)

**Checkpoint**: Modelo de datos de submissions listo — implementación de US5 y US6 puede comenzar.

---

## Phase 3: User Story 1 — Creación de usuario proveedor (Priority: P1) 🎯 MVP

**Goal**: Un administrador puede crear una cuenta con rol "proveedor" vinculada a una empresa, y ese usuario puede iniciar sesión y llegar directamente a su portal.

**Independent Test**: Crear usuario con rol supplier via API/UI → login → la sesión contiene `supplier_id` correcto → el frontend redirige a `/portal`.

### Tests críticos (Constitución Principio III — obligatorios antes del merge)

> **NOTA: Escribir estos tests ANTES de implementar T009/T010. Deben fallar hasta que la implementación esté completa.**

- [X] T005 [P] [US1] Crear `backend/tests/test_portal_auth.py` — tests: sin cookie → 401; rol admin/manager/viewer → 403; rol supplier sin supplier_id en sesión → 409; rol supplier con supplier_id válido → 200
- [X] T006 [P] [US1] Crear `backend/tests/test_portal_isolation.py` — test de aislamiento: supplier A no puede ver datos de supplier B en la misma organización; supplier de org X no puede ver datos de org Y

### Implementación backend

- [X] T007 [P] [US1] Extender `backend/src/repse/users/schemas.py` — agregar `supplier_id: int | None = None` a `UserOut`, `UserCreate` y `UserPatch`; agregar `@model_validator(mode="after")` en `UserCreate` que falle con ValidationError si `role == Role.SUPPLIER` y `supplier_id is None`
- [X] T008 [P] [US1] Extender `backend/src/repse/auth/dependencies.py` — agregar `supplier_id: int | None = None` a `CurrentUser`; propagar `payload.supplier_id` en la función `current_user()`
- [X] T009 [US1] Actualizar `backend/src/repse/users/routes.py` — en `create_user`: si `body.role == Role.SUPPLIER`, verificar que `body.supplier_id` existe y pertenece a `user.organization_id` (raise NotFound si no); asignar `new.supplier_id`; en `update_user`: si cambia a supplier validar supplier_id; si cambia desde supplier a otro rol setear `row.supplier_id = None` (depende de T007, T008)
- [X] T010 [US1] Actualizar `backend/src/repse/auth/routes.py` — en `login_local` y `callback` OIDC: incluir `supplier_id=user.supplier_id` al construir `SessionPayload`; en el endpoint `/me`: incluir `"supplier_id": user.supplier_id` en la respuesta JSON (depende de T008)

### Implementación frontend

- [X] T011 [P] [US1] Actualizar `frontend/src/lib/auth.tsx` — agregar `"supplier"` al type `Role`; agregar `supplierId?: number | null` a `AuthUser`
- [X] T012 [P] [US1] Actualizar `frontend/src/lib/api/index.ts` — agregar `"supplier"` al type `Role`; agregar `supplier_id?: number | null` a los tipos `UserItem` y `UserCreate`
- [X] T013 [US1] Actualizar `frontend/src/pages/users/list.tsx` — agregar `supplier: "Proveedor"` a `ROLE_LABEL`; agregar `<option value="supplier">` en los select de rol de la tabla y del diálogo; en `CreateUserDialog` cuando `role === "supplier"` mostrar select de empresa proveedora (query a `suppliersApi.list()`, solo activos); incluir `supplier_id` en el body de `usersApi.create()`; deshabilitar "Crear" si rol=supplier y sin empresa seleccionada (depende de T011, T012)

**Checkpoint**: Admin puede crear usuario proveedor, usuario hace login y la sesión tiene `supplier_id` correcto.

---

## Phase 4: User Story 2 — Vista de estado actual por tipo de documento (Priority: P2)

**Goal**: El proveedor abre el portal y ve el estado de cumplimiento de todos sus tipos de documento para el año actual, agrupados por tipo, con indicación visual del estado (vigente/próximo a vencer/vencido/pendiente/enviado).

**Independent Test**: Usuario con rol supplier hace `GET /api/v1/portal/compliance` → responde 200 con `ComplianceGridOut`; en frontend abre `/portal` → ve la cuadrícula de estados sin hacer ninguna acción adicional.

### Implementación backend

- [X] T014 [US2] Crear `backend/src/repse/portal/__init__.py` — archivo vacío de paquete
- [X] T015 [US2] Crear `backend/src/repse/portal/routes.py` — `GET /portal/compliance?year=N`: requiere `require_role(Role.SUPPLIER.value)`; obtiene `supplier_id` desde `user.supplier_id` (raise 409 Conflict con `code="supplier_not_linked"` si es None); valida rango año 2020–actual; llama `service.get_annual_compliance(db, supplier_id=user.supplier_id, organization_id=user.organization_id, year=effective_year)`; devuelve `ComplianceGridOut` (depende de T014)
- [X] T016 [US2] Actualizar `backend/src/repse/main.py` — importar el router de portal; incluirlo con prefijo `/api/v1` (depende de T015)

### Implementación frontend

- [X] T017 [P] [US2] Crear `frontend/src/lib/api/portal.ts` — exportar `portalApi` con método `getCompliance(year?: number): Promise<ComplianceGridOut>` que llama `GET /api/v1/portal/compliance${year ? \`?year=${year}\` : ""}`; reutilizar `apiFetch` del módulo api existente
- [X] T018 [US2] Actualizar `frontend/src/app/router.tsx` — importar `PortalPage` (nuevo); agregar `<Route path="portal" element={<PortalPage />} />`; cambiar el `<Navigate>` del índice raíz para que cuando `role === "supplier"` redirija a `/portal` y los demás a `/suppliers`; en `setUser` dentro de `RequireAuth` mapear `me.supplier_id` a `supplierId` en `AuthUser` (depende de T011, T017)
- [X] T019 [US2] Actualizar `frontend/src/components/layout/AppShell.tsx` — para `user?.role === "supplier"` mostrar solo el ítem "Mi documentación" (enlace a `/portal`, icono `FileStack`) en la navegación; ocultar todos los ítems administrativos; mantener visibles nombre de organización, RFC y botón de logout (depende de T011)
- [X] T020 [US2] Crear `frontend/src/pages/portal/index.tsx` — `PortalPage`: query `portalApi.getCompliance(selectedYear)` con TanStack Query; cabecera con nombre del proveedor, RFC, tipo de proveedor y `compliance_percent`; selector de año (rango 2020–año actual, default año en curso); para cada `monthly_requirement` mostrar fila con nombre del tipo y la fila de celdas usando el componente `ComplianceCell` existente; para `one_time_requirements` sección separada "Documentos únicos" (depende de T017, T018, T019)

**Checkpoint**: Usuario supplier ingresa al sistema, ve `/portal` con el grid de cumplimiento completo.

---

## Phase 5: User Story 5 — Carga de documentos faltantes o vencidos (Priority: P2)

**Goal**: El proveedor puede cargar archivos para celdas en estado `missing`, `expired` o `pending` directamente desde el portal sin intervención del administrador.

**Independent Test**: Proveedor con celda en estado "Faltante" selecciona esa celda, carga un archivo válido → estado de la celda se actualiza a `missing` con archivo en la misma sesión (< 3 s); intentar cargar en celda `submitted` retorna error explicativo.

### Tests críticos (Constitución Principio III — obligatorios antes del merge)

> **NOTA: Escribir estos tests ANTES de T030. Deben fallar hasta que la implementación esté completa.**

- [X] T030 [P] [US5] Crear `backend/tests/test_portal_upload.py` — tests negativos: período futuro → 422 `future_period`; celda en estado `submitted` → 409 `upload_not_allowed`; celda en estado `validated` → 409 `upload_not_allowed`; celda en estado `expiring_soon` → 409 `upload_not_allowed`; límite de archivos alcanzado (`max_files`) → 409 `max_files_reached`; formato inválido → 422 `invalid_file_type`; tamaño excedido → 422 `file_too_large`; test positivo: celda `missing` + archivo válido → 201

### Implementación backend

- [X] T031 [US5] Implementar endpoint `POST /api/v1/portal/upload` en `backend/src/repse/portal/routes.py` — `Content-Type: multipart/form-data`; extrae `supplier_id` de la sesión; valida: `coverage_period_start` ≤ primer día del mes actual (422 `future_period`); estado de celda = `missing`/`expired`/`pending` (409 `upload_not_allowed`); cuenta de archivos < `document_type.max_files` (409 `max_files_reached`); formato y tamaño contra catálogo (422 `invalid_file_type` / `file_too_large`); llama al servicio de documentos existente con `supplier_id=session.supplier_id, organization_id=session.organization_id`; devuelve `UploadOut` 201 (depende de T027, T028, T029)

### Implementación frontend

- [X] T032 [P] [US5] Extender `frontend/src/lib/api/portal.ts` — agregar `portalApi.upload(file: File, documentTypeId: number, coveragePeriodStart?: string): Promise<UploadOut>` que llama `POST /api/v1/portal/upload` con `multipart/form-data`; manejar errores 409/422 devolviendo el `code` de error para mensajes descriptivos
- [X] T033 [US5] Crear `frontend/src/components/portal/UploadPortalDialog.tsx` — dialog con: selector de archivo (drag & drop o click), validación de formato/tamaño en cliente antes de enviar, mensaje de error descriptivo cuando el estado de la celda bloquea la carga, feedback de progreso durante la subida, confirmación de éxito (depende de T032)
- [X] T034 [US5] Integrar `UploadPortalDialog` en `frontend/src/pages/portal/index.tsx` — mostrar botón/icono de carga solo en celdas con estado `missing`, `expired` o `pending`; al confirmar carga exitosa invalidar la query `getCompliance` para que la vista se actualice en < 3 s (SC-008) (depende de T020, T033)

**Checkpoint**: Proveedor puede cargar documentos desde el portal y el estado de la celda se actualiza visualmente.

---

## Phase 6: User Story 6 — Envío a validación por tipo de documento (Priority: P2)

**Goal**: El proveedor puede enviar un paquete de documentos a revisión de contabilidad con un clic; el estado de la celda cambia a "Pendiente de validación" en < 3 s y el botón queda inhabilitado hasta que contabilidad procese la solicitud.

**Independent Test**: Proveedor con al menos un archivo cargado presiona "Enviar a validar" → portal_submission creada con `status='pending'` → estado de celda cambia a `submitted` en frontend (< 3 s) → botón inhabilitado; proveedor no puede re-enviar sin acción de contabilidad.

### Tests críticos (Constitución Principio III — obligatorios antes del merge)

> **NOTA: Escribir estos tests ANTES de T036/T037. Deben fallar hasta que la implementación esté completa.**

- [X] T035 [P] [US6] Crear `backend/tests/test_portal_submit.py` — tests negativos: ningún documento cargado en la celda → 409 `no_documents_uploaded`; ya existe submission pendiente → 409 `already_submitted`; celda en estado `validated` → 409 `cell_not_submittable`; celda en estado `expiring_soon` → 409 `cell_not_submittable`; test positivo: celda con documentos cargados → 201 con `SubmissionOut`; test GET submission: celda con rejection → devuelve `rejection_reason`; celda sin submission → devuelve null

### Implementación backend

- [X] T036 [US6] Implementar endpoint `POST /api/v1/portal/submit/{document_type_id}` en `backend/src/repse/portal/routes.py` — body: `SubmitRequest(coverage_period_start: date | None)`; valida: al menos 1 documento en la celda (409 `no_documents_uploaded`); no existe `portal_submission` con `status='pending'` para esa celda (409 `already_submitted`); estado de celda ≠ `validated`/`expiring_soon` (409 `cell_not_submittable`); crea `PortalSubmission(status='pending', submitted_at=utcnow(), pre_submission_status=current_status, submitted_by=user.user_id)`; devuelve `SubmissionOut` 201 (depende de T027, T028)
- [X] T037 [P] [US6] Implementar endpoint `GET /api/v1/portal/submission/{document_type_id}` en `backend/src/repse/portal/routes.py` — query param `coverage_period_start`; devuelve la submission más reciente para esa celda con `submission_id`, `status`, `submitted_at`, `rejection_reason`, `rejected_at`; devuelve `null` si no existe submission previa (depende de T027, T028)

### Implementación frontend

- [X] T038 [P] [US6] Extender `frontend/src/lib/api/portal.ts` — agregar `portalApi.submit(documentTypeId: number, coveragePeriodStart: string | null): Promise<SubmissionOut>` que llama `POST /api/v1/portal/submit/{documentTypeId}`; agregar `portalApi.getSubmission(documentTypeId: number, coveragePeriodStart?: string): Promise<SubmissionDetail | null>` que llama `GET /api/v1/portal/submission/{documentTypeId}`
- [X] T039 [US6] Crear `frontend/src/components/portal/SubmitValidationButton.tsx` — botón CTA con color de acción destacado (no gris/neutro); muestra diálogo de confirmación antes de enviar; inhabilita el botón tras envío exitoso (estado `submitted`); estado de carga durante la petición; visible solo cuando la celda tiene al menos 1 archivo y no hay submission pendiente (depende de T038)
- [X] T040 [P] [US6] Crear `frontend/src/components/portal/RejectionReasonBanner.tsx` — banner visible cuando `portalApi.getSubmission()` devuelve `status='rejected'`; muestra el `rejection_reason` de contabilidad; usa color de advertencia/error; desaparece cuando el proveedor carga nuevamente (celda sale de estado rechazado) (depende de T038)
- [X] T041 [US6] Integrar `SubmitValidationButton` y `RejectionReasonBanner` en `frontend/src/pages/portal/index.tsx` — botón visible en celdas que tienen archivos y no tienen submission pending; banner visible cuando la última submission fue rechazada; invalidar query `getCompliance` tras submit exitoso para actualizar estado a `submitted` en < 3 s (SC-010) (depende de T020, T039, T040)

**Checkpoint**: Flujo completo upload → submit → estado `submitted` visible en portal; banner de rechazo visible tras rechazo de contabilidad.

---

## Phase 7: User Story 3 — Consulta del historial de documentos por tipo (Priority: P3)

**Goal**: El proveedor puede seleccionar un tipo de documento y ver el historial completo de entregas: todas las versiones, períodos de vigencia y estados.

**Independent Test**: Hacer clic en un tipo de documento en el portal abre una vista con la lista de todas las entregas históricas ordenadas por período desc, o un mensaje "sin registros" si no hay nada.

### Implementación backend

- [X] T021 [US3] Extender `backend/src/repse/portal/routes.py` — agregar `GET /portal/history/{document_type_id}`: requiere `require_role(Role.SUPPLIER.value)`; consulta todos los `Document` donde `supplier_id=user.supplier_id`, `document_type_id=document_type_id`, `organization_id=user.organization_id`, `deleted_at IS NULL`; ordena por `coverage_period_start DESC, version DESC`; devuelve lista con campos: `id`, `version`, `is_latest`, `coverage_period_start`, `coverage_period_end`, `due_date_effective`, `status`, `file_name_original`, `uploaded_by`, `created_at` (depende de T015)

### Implementación frontend

- [X] T022 [P] [US3] Extender `frontend/src/lib/api/portal.ts` — agregar método `getDocumentHistory(documentTypeId: number): Promise<DocumentHistoryItem[]>` que llama `GET /api/v1/portal/history/{documentTypeId}`; definir el tipo `DocumentHistoryItem` con los campos del endpoint
- [X] T023 [US3] Extender `frontend/src/pages/portal/index.tsx` — agregar estado `selectedDocType` (document_type_id | null); al hacer clic en una fila de tipo de documento setear `selectedDocType`; mostrar panel/drawer lateral o sección expandible que cargue `portalApi.getDocumentHistory(selectedDocType)` y liste cada entrega con: nombre de archivo, período de vigencia, estado (`ComplianceBadge`), versión; mostrar mensaje vacío si no hay registros (depende de T020, T022)

**Checkpoint**: El proveedor puede ver el detalle histórico de cualquier tipo de documento directamente desde el portal.

---

## Phase 8: User Story 4 — Documentos próximos a vencer con acceso rápido (Priority: P4)

**Goal**: El portal presenta una sección de alertas visible al entrar que lista los tipos de documento que vencen pronto o ya están vencidos, permitiendo acción rápida.

**Independent Test**: Cuando al menos un documento tiene status `missing`, `expired` o `pending` en el mes actual, la sección de alertas aparece al entrar al portal con ese tipo listado y los días restantes.

### Implementación frontend

- [X] T024 [US4] Extender `frontend/src/pages/portal/index.tsx` — agregar sección "Alertas" encima del grid: filtrar de `monthly_requirements` las celdas del mes actual que tengan status `missing`, `expired` o `pending`; más todos los `one_time_requirements` con esos mismos estados; si hay alertas, renderizar una card destacada con la lista (badge de estado, nombre del tipo, días hasta vencimiento si `due_date_effective` disponible); si no hay alertas, mostrar mensaje de cumplimiento al día; hacer clic en un ítem de alerta debe llevar al tipo correspondiente en el grid (usando `selectedDocType`) (depende de T020)

**Checkpoint**: El proveedor ve inmediatamente qué documentos requieren atención al ingresar al portal.

---

## Phase 9: Polish & Validación cruzada

**Purpose**: Verificación funcional del flujo completo y validaciones de seguridad.

- [ ] T025 [P] Validación manual end-to-end: crear usuario proveedor via UI admin → login como proveedor → verificar redirección a `/portal` → verificar nav mínima → verificar grid de cumplimiento → cargar documento en celda `missing` → verificar actualización de estado → presionar "Enviar a validar" → verificar estado `submitted` → verificar historial → verificar alertas → verificar que navegar a `/suppliers` redirige a `/portal`
- [ ] T042 [P] Verificar que ningún endpoint del portal acepta `supplier_id` como parámetro externo (query/body/path); revisar `backend/src/repse/portal/routes.py` contra el contrato en `specs/009-proveedor-portal-viewer/contracts/portal-compliance.md`
- [ ] T043 [P] Verificar respuesta `GET /api/v1/portal/compliance` < 500 ms p95 con datos reales de un proveedor con 12 meses de histórico; agregar índices adicionales a `portal_submissions` si la query de submissions pending supera el umbral (SC-002)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Sin dependencias — comenzar de inmediato
- **Phase 2 (Foundational Part 1)**: Depende de Phase 1 — bloquea todas las historias
- **Phase 2B (Foundational Part 2)**: Depende de Phase 2 — bloquea US5 y US6
- **Phase 3 (US1)**: Depende de Phase 2
- **Phase 4 (US2)**: Depende de Phase 2; puede ejecutarse en paralelo con US1
- **Phase 5 (US5)**: Depende de Phase 2B y Phase 4 (PortalPage base debe existir para integración frontend)
- **Phase 6 (US6)**: Depende de Phase 2B y Phase 5 (flujo upload → submit)
- **Phase 7 (US3)**: Depende de Phase 4 (extiende portal/routes.py y PortalPage existentes)
- **Phase 8 (US4)**: Depende de Phase 4 (usa datos del compliance grid)
- **Phase 9 (Polish)**: Depende de todas las historias completadas

### User Story Dependencies

- **US1 (P1)**: Puede comenzar después de Phase 2. Sin dependencias en otras historias.
- **US2 (P2)**: Depende de US1 (el portal endpoint necesita `CurrentUser.supplier_id` de T008).
- **US5 (P2)**: Depende de Phase 2B y US2 (integración en PortalPage existente).
- **US6 (P2)**: Depende de US5 (el flujo de envío supone que hay archivos cargados).
- **US3 (P3)**: Depende de US2 (extiende portal/routes.py y PortalPage existentes).
- **US4 (P4)**: Depende de US2 (usa el mismo compliance grid).

### Within Each User Story

- Tests: escribir ANTES de la implementación correspondiente; deben fallar hasta que esté completa
- Modelos y schemas antes que routes
- Backend antes que frontend en cada historia
- Para US5/US6: completar backend primero, luego frontend

### Parallel Opportunities

- T026, T027, T028 (Phase 2B): archivos distintos, paralelos
- T030, T032 (US5): tests y API client paralelos con T031 backend
- T035, T037, T038, T040 (US6): paralelos entre sí
- T039 (SubmitValidationButton) y T040 (RejectionReasonBanner): archivos distintos, paralelos

---

## Parallel Example: User Story 5

```text
# Ejecutar en paralelo después de Phase 2B completa:
T030 — test_portal_upload.py (tests de upload)
T032 — portal.ts upload method
T031 — POST /upload endpoint (secuencial: requiere T030 fallando)

# Después de T031 + T032:
T033 — UploadPortalDialog
T034 — Integración en PortalPage
```

## Parallel Example: User Story 6

```text
# Ejecutar en paralelo después de Phase 2B completa:
T035 — test_portal_submit.py
T037 — GET /submission endpoint
T038 — portal.ts submit/getSubmission
T039 — SubmitValidationButton
T040 — RejectionReasonBanner

# T036 (POST /submit) requiere T035 fallando primero
# T041 integración en PortalPage requiere T036 + T039 + T040
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Completar Phase 1 + Phase 2 (Setup + Foundational)
2. Completar Phase 3 (US1 — Creación de usuario proveedor) — **YA COMPLETO** (excepto T005/T006)
3. Completar Phase 4 (US2 — Vista de estado actual) — **YA COMPLETO**
4. **STOP y VALIDAR**: el proveedor puede iniciar sesión y ver su portal con el grid de cumplimiento

### Incremental Delivery

1. Setup + Foundational → Base de datos y sesión actualizadas — **YA COMPLETO**
2. T005/T006 → Tests de auth e aislamiento de tenant — **YA COMPLETO** (Constitución Principio III)
3. US1 → Admin puede crear proveedores; proveedor puede hacer login — **YA COMPLETO**
4. US2 → Proveedor ve su portal con estados — **YA COMPLETO**
5. Phase 2B → Modelos para upload/submit — **YA COMPLETO**
6. US5 → Proveedor carga documentos desde portal — **YA COMPLETO**
7. US6 → Proveedor envía a validación — **YA COMPLETO**
8. US3 → Proveedor revisa historial — **YA COMPLETO**
9. US4 → Alertas destacadas — **YA COMPLETO**
10. Phase 9 → Validación manual end-to-end — **PENDIENTE**

### Parallel Team Strategy

Con múltiples desarrolladores, una vez completada Phase 2B:
- Dev A: US5 backend (POST /upload) + tests
- Dev B: US6 backend (POST /submit + GET /submission) + tests
- Dev C: US5/US6 frontend (UploadPortalDialog, SubmitValidationButton, RejectionReasonBanner)

---

## Notes

- **[P]** = archivos distintos, sin dependencias pendientes entre sí — ejecutables en paralelo
- Los tests T030/T035 son **OBLIGATORIOS** (Constitution Principio III) — no son opcionales
- Los tests T005/T006 (auth/aislamiento) son obligatorios — ya completados
- Las cookies de sesión anteriores (sin `supplier_id`) son backward-compatible con `supplier_id=None`
- La migración T026 requiere `op.execute(text(...))` en Alembic para el CREATE TABLE completo (el proyecto usa MySQL 8)
- `supplier_id` NUNCA se acepta como parámetro externo en ningún endpoint del portal; siempre de la sesión firmada
- El aislamiento multi-tenant se aplica con `organization_id` en todas las queries de `portal_submissions`
- La interfaz de contabilidad (aprobar/rechazar submissions) está **fuera del alcance** de esta feature; solo se entregan los datos y el endpoint de submit
- `ComplianceCell` y `ComplianceBadge` existentes no necesitan modificaciones para el portal
- Cuando contabilidad rechaza (feature separada), el `pre_submission_status` en `portal_submissions` indica a qué estado debe volver la celda
