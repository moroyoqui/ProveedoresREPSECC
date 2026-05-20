# Tasks: Portal del Proveedor — Visor de Documentación

**Input**: Design documents from `specs/009-proveedor-portal-viewer/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅

**Tests**: Se incluyen los tests de autenticación y aislamiento de tenant porque son **obligatorios** según el Principio III de la Constitución (caminos críticos de auth e isolation deben tener pruebas antes del merge).

**Organization**: Tareas agrupadas por historia de usuario del spec para permitir implementación y prueba independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece la tarea (US1–US4 según spec.md)

---

## Phase 1: Setup (Infraestructura compartida)

**Purpose**: Crear la estructura del nuevo paquete `portal` en el backend.

- [X] T001 Crear directorio `backend/src/repse/portal/` (paquete Python vacío)

---

## Phase 2: Foundational (Prerrequisitos bloqueantes)

**Purpose**: Cambios en BD y en la capa de sesión que bloquean TODAS las historias de usuario.

**⚠️ CRÍTICO**: Ninguna historia puede comenzar hasta que esta fase esté completa.

- [X] T002 Crear migración `backend/alembic/versions/0005_add_supplier_role_and_user_supplier_link.py` — upgrade: ALTER TABLE users MODIFY role ENUM añadiendo 'supplier'; ADD COLUMN supplier_id BIGINT NULL FK → suppliers.id ON DELETE SET NULL; CREATE INDEX ix_users_supplier
- [X] T003 [P] Extender `backend/src/repse/users/models.py` — agregar `SUPPLIER = "supplier"` al enum `Role`; agregar campo `supplier_id: Mapped[int | None]` con FK a `suppliers.id` ON DELETE SET NULL e index=True
- [X] T004 [P] Extender `backend/src/repse/auth/session.py` — agregar `supplier_id: int | None = None` a `SessionPayload`; actualizar `issue()` para incluir `"supplier_id": payload.supplier_id`; actualizar `read()` usando `.get("supplier_id")` (backward-compatible con cookies antiguas)

**Checkpoint**: Migración lista y modelos actualizados — pueden comenzar todas las historias.

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

**Goal**: El proveedor abre el portal y ve el estado de cumplimiento de todos sus tipos de documento para el año actual, agrupados por tipo, con indicación visual del estado (vigente/próximo a vencer/vencido/pendiente).

**Independent Test**: Usuario con rol supplier hace `GET /api/v1/portal/compliance` → responde 200 con `ComplianceGridOut`; en frontend abre `/portal` → ve la cuadrícula de estados sin hacer ninguna acción adicional.

### Implementación backend

- [X] T014 [US2] Crear `backend/src/repse/portal/__init__.py` — archivo vacío de paquete
- [X] T015 [US2] Crear `backend/src/repse/portal/routes.py` — `GET /portal/compliance?year=N`: requiere `require_role(Role.SUPPLIER.value)`; obtiene `supplier_id` desde `user.supplier_id` (raise 409 Conflict con `code="supplier_not_linked"` si es None); valida rango año 2020–actual; llama `service.get_annual_compliance(db, supplier_id=user.supplier_id, organization_id=user.organization_id, year=effective_year)`; devuelve `ComplianceGridOut` (depende de T014)
- [X] T016 [US2] Actualizar `backend/src/repse/main.py` — importar el router de portal; incluirlo con prefijo `/api/v1` (depende de T015)

### Implementación frontend

- [X] T017 [P] [US2] Crear `frontend/src/lib/api/portal.ts` — exportar `portalApi` con método `getCompliance(year?: number): Promise<ComplianceGridOut>` que llama `GET /api/v1/portal/compliance${year ? \`?year=${year}\` : ""}`; reutilizar `apiFetch` del módulo api existente
- [X] T018 [US2] Actualizar `frontend/src/app/router.tsx` — importar `PortalPage` (nuevo); agregar `<Route path="portal" element={<PortalPage />} />`; cambiar el `<Navigate>` del índice raíz para que cuando `role === "supplier"` redirija a `/portal` y los demás a `/suppliers`; en `setUser` dentro de `RequireAuth` mapear `me.supplier_id` a `supplierId` en `AuthUser` (depende de T011, T017)
- [X] T019 [US2] Actualizar `frontend/src/components/layout/AppShell.tsx` — para `user?.role === "supplier"` mostrar solo el ítem "Mi documentación" (enlace a `/portal`, icono `FileStack`) en la navegación; ocultar todos los ítems administrativos; mantener visibles nombre de organización, RFC y botón de logout (depende de T011)
- [X] T020 [US2] Crear `frontend/src/pages/portal/index.tsx` — `PortalPage`: query `portalApi.getCompliance(selectedYear)` con TanStack Query; cabecera con nombre del proveedor, RFC, tipo de proveedor y `compliance_percent`; selector de año (rango 2020–año actual, default año en curso); para cada `monthly_requirement` mostrar fila con nombre del tipo y la fila de celdas usando el componente `ComplianceCell` existente; para `one_time_requirements` sección separada "Documentos únicos"; sin botones de acción (read-only) (depende de T017, T018, T019)

**Checkpoint**: Usuario supplier ingresa al sistema, ve `/portal` con el grid de cumplimiento completo.

---

## Phase 5: User Story 3 — Consulta del historial de documentos por tipo (Priority: P3)

**Goal**: El proveedor puede seleccionar un tipo de documento y ver el historial completo de entregas: todas las versiones, períodos de vigencia y estados.

**Independent Test**: Hacer clic en un tipo de documento en el portal abre una vista con la lista de todas las entregas históricas ordenadas por período desc, o un mensaje "sin registros" si no hay nada.

### Implementación backend

- [X] T021 [US3] Extender `backend/src/repse/portal/routes.py` — agregar `GET /portal/history/{document_type_id}`: requiere `require_role(Role.SUPPLIER.value)`; consulta todos los `Document` donde `supplier_id=user.supplier_id`, `document_type_id=document_type_id`, `organization_id=user.organization_id`, `deleted_at IS NULL`; ordena por `coverage_period_start DESC, version DESC`; devuelve lista con campos: `id`, `version`, `is_latest`, `coverage_period_start`, `coverage_period_end`, `due_date_effective`, `status`, `file_name_original`, `uploaded_by`, `created_at` (depende de T015)

### Implementación frontend

- [X] T022 [P] [US3] Extender `frontend/src/lib/api/portal.ts` — agregar método `getDocumentHistory(documentTypeId: number): Promise<DocumentHistoryItem[]>` que llama `GET /api/v1/portal/history/{documentTypeId}`; definir el tipo `DocumentHistoryItem` con los campos del endpoint
- [X] T023 [US3] Extender `frontend/src/pages/portal/index.tsx` — agregar estado `selectedDocType` (document_type_id | null); al hacer clic en una fila de tipo de documento setear `selectedDocType`; mostrar panel/drawer lateral o sección expandible que cargue `portalApi.getDocumentHistory(selectedDocType)` y liste cada entrega con: nombre de archivo, período de vigencia, estado (`ComplianceBadge`), versión; mostrar mensaje vacío si no hay registros (depende de T020, T022)

**Checkpoint**: El proveedor puede ver el detalle histórico de cualquier tipo de documento directamente desde el portal.

---

## Phase 6: User Story 4 — Documentos próximos a vencer con acceso rápido (Priority: P4)

**Goal**: El portal presenta una sección de alertas visible al entrar que lista los tipos de documento que vencen pronto o ya están vencidos, permitiendo acción rápida.

**Independent Test**: Cuando al menos un documento tiene status `missing`, `expired` o `pending` en el mes actual, la sección de alertas aparece al entrar al portal con ese tipo listado y los días restantes.

### Implementación frontend

- [X] T024 [US4] Extender `frontend/src/pages/portal/index.tsx` — agregar sección "Alertas" encima del grid: filtrar de `monthly_requirements` las celdas del mes actual que tengan status `missing`, `expired` o `pending`; más todos los `one_time_requirements` con esos mismos estados; si hay alertas, renderizar una card destacada con la lista (badge de estado, nombre del tipo, días hasta vencimiento si `due_date_effective` disponible); si no hay alertas, mostrar mensaje de cumplimiento al día; hacer clic en un ítem de alerta debe llevar al tipo correspondiente en el grid (usando `selectedDocType`) (depende de T020)

**Checkpoint**: El proveedor ve inmediatamente qué documentos requieren atención al ingresar al portal.

---

## Phase 7: Polish & Validación cruzada

**Purpose**: Verificación funcional del flujo completo.

- [ ] T025 [P] Validación manual end-to-end: crear usuario proveedor via UI admin → login como proveedor → verificar redirección a `/portal` → verificar que la nav solo muestra "Mi documentación" → verificar grid de cumplimiento → verificar historial de un tipo → verificar sección de alertas → verificar que intentar navegar a `/suppliers` redirige a `/portal`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Sin dependencias — comenzar de inmediato
- **Phase 2 (Foundational)**: Depende de Phase 1 — **bloquea todas las historias**
- **Phases 3–6 (User Stories)**: Dependen de Phase 2
  - US1 → US2 → US3 → US4 deben seguir ese orden (cada una construye sobre la anterior)
- **Phase 7 (Polish)**: Depende de todas las historias completadas

### User Story Dependencies

- **US1 (P1)**: Puede comenzar después de Phase 2. Sin dependencias en otras historias.
- **US2 (P2)**: Depende de US1 (el portal endpoint necesita `CurrentUser.supplier_id` de T008).
- **US3 (P3)**: Depende de US2 (la página del portal T020 debe existir antes de extenderla).
- **US4 (P4)**: Depende de US2 (igual, extiende T020).

### Within Each User Story

- Tests T005/T006: escribir ANTES de T009/T010; deben fallar hasta que la implementación esté lista
- Modelos y schemas antes que routes
- Backend antes que frontend en cada historia (el frontend necesita saber la forma del API)
- Para US2–US4: completar backend primero, luego frontend

### Parallel Opportunities

- T003 y T004 (foundational): archivos distintos, paralelos
- T005, T006, T007, T008 (inicio de US1): todos en archivos distintos, paralelos
- T011 y T012 (frontend types): archivos distintos, paralelos
- T017 (portal.ts) con T018 (router.tsx) con T019 (AppShell): paralelos
- T022 (portal.ts extensión) con T021 (backend history endpoint): paralelos

---

## Parallel Example: User Story 1

```text
# Ejecutar en paralelo después de Phase 2:
T005 — test_portal_auth.py (tests de auth gate)
T006 — test_portal_isolation.py (test de aislamiento)
T007 — users/schemas.py (supplier_id + validator)
T008 — auth/dependencies.py (CurrentUser.supplier_id)
T011 — frontend/lib/auth.tsx ("supplier" role)
T012 — frontend/lib/api/index.ts (supplier_id types)

# Después de T007 + T008:
T009 — users/routes.py (validación supplier_id)
T010 — auth/routes.py (login + /me + OIDC)

# Después de T011 + T012:
T013 — pages/users/list.tsx (CreateUserDialog supplier select)
```

## Parallel Example: User Story 2

```text
# Ejecutar en paralelo después de US1 completa:
T017 — frontend/lib/api/portal.ts
T014+T015+T016 — portal backend (secuencial entre sí)

# Después de T011 + T017:
T018 — app/router.tsx

# Después de T011:
T019 — AppShell.tsx

# Después de T017 + T018 + T019:
T020 — pages/portal/index.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Completar Phase 1 + Phase 2 (Setup + Foundational)
2. Completar Phase 3 (US1 — Creación de usuario proveedor)
3. Completar Phase 4 (US2 — Vista de estado actual)
4. **STOP y VALIDAR**: el proveedor puede iniciar sesión y ver su portal con el grid de cumplimiento
5. Demo/validación con stakeholders antes de continuar

### Incremental Delivery

1. Setup + Foundational → Base de datos y sesión actualizadas
2. US1 → Admin puede crear proveedores; proveedor puede hacer login → **MVP funcional**
3. US2 → Proveedor ve su portal con estados → **Valor real para el proveedor**
4. US3 → Proveedor puede revisar historial → **Transparencia de cumplimiento**
5. US4 → Alertas destacadas → **Priorización de acción**

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes entre sí
- Los tests T005/T006 son OBLIGATORIOS (Constitution Principio III) — no son opcionales
- Las cookies de sesión anteriores (sin `supplier_id`) son backward-compatible con `supplier_id=None`
- La migración T002 requiere ALTER TABLE sobre el ENUM MySQL; usar `op.execute(text(...))` en Alembic ya que el proyecto usa `native_enum=False`
- `ComplianceCell` y `ComplianceBadge` existentes no necesitan modificaciones para el portal
- No agregar endpoints POST/PATCH/DELETE al módulo `portal/` en esta iteración
