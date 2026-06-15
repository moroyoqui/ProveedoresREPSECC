# Tasks: Separación de Pantallas de Carga y Consulta en el Portal del Proveedor

**Input**: Design documents from `/specs/013-portal-upload-separation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-and-routes.md, quickstart.md

**Tests**: Incluidos solo para rutas críticas de auth/autorización (obligatorios por Constitución Principio III): gating de audiencia en login y verificación de solo-lectura/403 cruzados. Se escriben ANTES de la implementación que validan.

**Organization**: Tareas agrupadas por user story. Prioridades: US1 (P1), US2 (P2), US4 (P2), US3 (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: User story a la que pertenece (US1–US4)

## Path Conventions

Web app: `backend/src/repse/`, `backend/tests/`, `frontend/src/` (ver plan.md).

---

## Phase 1: Setup

**Purpose**: Línea base verificada antes de tocar código

- [X] T001 Correr línea base en verde: `cd backend && pytest tests/test_portal_auth.py tests/test_portal_isolation.py tests/test_portal_upload.py tests/test_portal_submit.py -q` y `cd frontend && npm run build`; anotar cualquier fallo preexistente antes de iniciar

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Layout y estructura de rutas del portal de las que dependen US1, US2 y US4

**⚠️ CRITICAL**: Ninguna user story puede comenzar sin esta fase

- [X] T002 Crear layout `PortalShell` en `frontend/src/components/layout/PortalShell.tsx`: menú exclusivo con entradas Consulta (`/portal/consulta`) y Carga (`/portal/carga`), datos de organización/usuario, botón cerrar sesión e identidad visual del portal (sin reutilizar el NAV administrativo de `AppShell.tsx`)
- [X] T003 Reestructurar `frontend/src/app/router.tsx`: guard `RequireSupplier` (supplier exigido; admin/analyst → redirect a su área), ruta `/portal` → `Navigate replace` a `/portal/consulta` (FR-006), y rutas `/portal/consulta` y `/portal/carga` montadas bajo `PortalShell` + `RequireSupplier`; las rutas administrativas conservan `RequireNonSupplier` y `AppShell`

**Checkpoint**: El esqueleto de rutas del portal renderiza bajo `PortalShell` (páginas aún provisionales)

---

## Phase 3: User Story 1 - Pantallas independientes de consulta y de carga (Priority: P1) 🎯 MVP

**Goal**: `/portal/consulta` estrictamente de solo lectura y `/portal/carga` solo con celdas elegibles y acciones de carga/envío; la página combinada desaparece

**Independent Test**: Un supplier autenticado recorre `/portal/consulta` sin encontrar ningún control de carga/envío (SC-001), y `/portal/carga` muestra únicamente celdas `missing`/`expired` con el flujo de carga y envío funcionando como en 009

### Implementation for User Story 1

- [X] T004 [P] [US1] Crear `frontend/src/pages/portal/consulta.tsx` moviendo desde `frontend/src/pages/portal/index.tsx` el grid de cumplimiento, alertas, historial y `RejectionReasonBanner`, eliminando todo control de carga y envío (FR-002); conservar queries TanStack existentes (`portalApi.getCompliance`, `getDocumentHistory`, `getSubmission`)
- [X] T005 [P] [US1] Crear `frontend/src/pages/portal/carga.tsx` moviendo desde `frontend/src/pages/portal/index.tsx` la lista de celdas elegibles (`missing`/`expired`, sin períodos futuros), `UploadPortalDialog` y `SubmitValidationButton` (FR-003, FR-007); cuando no hay celdas elegibles mostrar mensaje positivo de cumplimiento (edge case spec)
- [X] T006 [US1] Eliminar `frontend/src/pages/portal/index.tsx`, actualizar imports en `frontend/src/app/router.tsx` para usar las páginas de T004/T005 y verificar que no queda ninguna referencia (`grep PortalPage`)
- [X] T007 [US1] Verificar SC-001/SC-005: `grep -i "UploadPortalDialog\|SubmitValidationButton\|portalApi.upload\|portalApi.submit" frontend/src/pages/portal/consulta.tsx` sin resultados; flujo completo de carga y envío en `/portal/carga` funciona igual que en 009 (verificación manual según quickstart.md pasos 3–4)

**Checkpoint**: US1 funcional — pantallas separadas con el comportamiento de 009 intacto

---

## Phase 4: User Story 2 - Navegación con contexto entre consulta y carga (Priority: P2)

**Goal**: Desde una celda elegible en Consulta se llega a Carga con tipo y período preseleccionados en una acción; al volver, el estado está actualizado

**Independent Test**: Clic en "Ir a cargar" sobre una celda `missing` en `/portal/consulta` abre `/portal/carga?type={id}&period={YYYY-MM-01}` con esa celda preseleccionada; tras cargar y enviar, `/portal/consulta` muestra "Pendiente de validación" sin recarga manual

### Implementation for User Story 2

- [X] T008 [US2] Agregar acción "Ir a cargar" en celdas `missing`/`expired` de `frontend/src/pages/portal/consulta.tsx` que navega a `/portal/carga?type={document_type_id}&period={coverage_period_start}`; no ofrecerla en celdas `vigente`/`expiring_soon`/`pendiente de validación` (FR-004, escenarios US2)
- [X] T009 [US2] Leer `type`/`period` con `useSearchParams` en `frontend/src/pages/portal/carga.tsx` y preseleccionar/enfocar la celda correspondiente; ignorar parámetros que no correspondan a una celda elegible
- [X] T010 [US2] Garantizar FR-011 en `frontend/src/pages/portal/carga.tsx`: tras upload o submit exitoso invalidar la query de compliance del portal (`queryClient.invalidateQueries` con la key usada por `portalApi.getCompliance`) para que `/portal/consulta` refleje el nuevo estado sin recarga

**Checkpoint**: US1 + US2 funcionan; el flujo detectar→cargar→ver estado cuesta máximo 1 clic adicional (SC-002)

---

## Phase 5: User Story 4 - Acceso y menú independientes para proveedores (Priority: P2)

**Goal**: Login dedicado `/portal/login` con gating por audiencia; menú del proveedor sin rastro del back-office y viceversa

**Independent Test**: Supplier entra por `/portal/login` y aterriza en `/portal/consulta` con menú de solo Consulta/Carga/cerrar sesión; el mismo supplier en `/login` recibe el mensaje genérico de credenciales; un admin en `/portal/login` recibe el mismo mensaje genérico (SC-008, SC-009)

### Tests for User Story 4 (test-first, Constitución III) ⚠️

> Escribir primero y comprobar que FALLAN antes de implementar T012

- [X] T011 [US4] Crear `backend/tests/test_auth_entry.py`: (a) login sin `audience` se comporta como hoy para roles no-supplier (retrocompatibilidad); (b) `audience="portal"` + rol supplier → 200 con cookie; (c) `audience="portal"` + rol admin → 422 con body idéntico al de credenciales inválidas; (d) `audience="backoffice"` (y omitido) + rol supplier → 422 idéntico a credenciales inválidas; (e) `audience` inválido → 422 de validación; comparar código y estructura del error byte-a-byte entre (c)/(d) y el caso de contraseña incorrecta (FR-013, contrato auth-and-routes.md)

### Implementation for User Story 4

- [X] T012 [US4] Agregar `audience: Literal["backoffice","portal"] = "backoffice"` a `LoginIn` y la regla de mismatch (tras `verify_password`: rol supplier ⇔ audiencia portal; si no coincide, levantar exactamente el mismo `ValidationFailure invalid_credentials`) en `backend/src/repse/auth/routes.py` (función `login_local`, líneas 159–212); correr T011 hasta verde
- [X] T013 [P] [US4] Crear `frontend/src/pages/portal/login.tsx`: solo correo+contraseña con `audience: "portal"` en el POST a `/auth/login`, identidad visual del portal, navegación a `/portal/consulta` tras éxito, mensaje genérico de error y enlace estático "¿Personal administrativo? Entra por aquí" → `/login` (FR-012, Decision 3)
- [X] T014 [US4] Registrar `/portal/login` en `frontend/src/app/router.tsx` (fuera de `RequireAuth`); si ya hay sesión supplier activa, redirigir a `/portal/consulta`
- [X] T015 [P] [US4] En `frontend/src/pages/auth/login.tsx`: enviar `audience: "backoffice"` en el POST y agregar enlace estático "¿Eres proveedor? Entra por el portal" → `/portal/login` (FR-013, orientación en UI)
- [X] T016 [US4] Eliminar la rama condicional supplier de `frontend/src/components/layout/AppShell.tsx` (líneas 71–84) dejando `AppShell` exclusivo del back-office; verificar que ninguna sesión supplier renderiza `AppShell` (el router de T003 la dirige a `PortalShell`)

**Checkpoint**: Mundos separados de extremo a extremo: puerta, menú y pantallas

---

## Phase 6: User Story 3 - Segregación de servicios por audiencia (Priority: P3)

**Goal**: Router del portal dividido en read (solo GET, cero escrituras) y write (POST), mismas URLs; matriz de autorización verificada por tests

**Independent Test**: Suites nuevas y de 009 en verde; con credencial supplier todo endpoint administrativo responde 403 y con credencial admin todo endpoint del portal responde 403 (SC-003); ningún handler del grupo read escribe a BD (SC-004)

### Tests for User Story 3 (test-first, Constitución III) ⚠️

> Escribir primero y comprobar que FALLAN (o pasan solo parcialmente) antes del split

- [X] T017 [US3] Crear `backend/tests/test_portal_read_only.py`: (a) recorrer las rutas montadas bajo `/api/v1/portal` y asertar que `routes_read` solo registra método GET; (b) llamar los 3 GET con supplier y verificar que no insertan/modifican filas (conteos antes/después en `documents` y `portal_submissions`); (c) credencial supplier → 403 en endpoints administrativos representativos (`GET /api/v1/suppliers`, `GET /api/v1/users`, `POST /api/v1/documents`-equivalente, `GET /api/v1/document-types`); (d) credencial admin → 403 en los 5 endpoints del portal (matriz de contracts/auth-and-routes.md)

### Implementation for User Story 3

- [X] T018 [P] [US3] Crear `backend/src/repse/portal/routes_read.py` moviendo sin cambio de lógica `portal_compliance`, `portal_document_history` y `portal_get_submission` desde `backend/src/repse/portal/routes.py` (FR-009, Decision 5)
- [X] T019 [P] [US3] Crear `backend/src/repse/portal/routes_write.py` moviendo sin cambio de lógica `portal_upload`, `portal_submit` y `_check_upload_allowed` desde `backend/src/repse/portal/routes.py`
- [X] T020 [US3] Actualizar `backend/src/repse/main.py` para montar ambos routers bajo `{API_PREFIX}/portal` (tags `portal-read`/`portal-write`), eliminar `backend/src/repse/portal/routes.py` y ajustar `backend/src/repse/portal/__init__.py` si exporta el router anterior; correr T017 hasta verde
- [X] T021 [US3] Regresión FR-007/SC-005: `cd backend && pytest tests/test_portal_auth.py tests/test_portal_isolation.py tests/test_portal_upload.py tests/test_portal_submit.py tests/test_auth_entry.py tests/test_portal_read_only.py -q` todo en verde sin modificar lógica de negocio

**Checkpoint**: Las cuatro user stories funcionan de forma independiente

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T022 Correr suite completa backend (`cd backend && pytest -q`) y build+tests frontend (`cd frontend && npm run build && npm test -- --run` si hay suite vitest) — todo en verde
- [X] T023 Validación manual de quickstart.md (pasos 1–6): login por ambas puertas, menú exclusivo, separación de pantallas, preselección con contexto, refresco de estado y redirects cruzados

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias
- **Foundational (Phase 2)**: tras Phase 1 — BLOQUEA todas las stories (T003 depende de T002)
- **US1 (Phase 3)**: tras Phase 2
- **US2 (Phase 4)**: tras US1 (edita `consulta.tsx`/`carga.tsx` creados en US1)
- **US4 (Phase 5)**: tras Phase 2; independiente de US1/US2 en backend (T011/T012); T013–T016 solo requieren el router de T003
- **US3 (Phase 6)**: tras Phase 1; independiente de todo el frontend — puede avanzar en paralelo con Phases 3–5
- **Polish (Phase 7)**: tras todas las stories

### Within Each User Story

- T011 antes de T012 (test-first); T017 antes de T018–T020 (test-first)
- T004 y T005 en paralelo; T006 después de ambos
- T018 y T019 en paralelo; T020 después de ambos

### Parallel Opportunities

- US3 completa (T017–T021, solo backend) en paralelo con US1/US2/US4 (mayormente frontend)
- Dentro de US4: T011 (backend) en paralelo con T013/T015 (frontend); T012 tras T011
- T004 ∥ T005; T013 ∥ T015; T018 ∥ T019

## Parallel Example: arranque tras Phase 2

```bash
# Desarrollador A (frontend):
Task: "T004 Crear consulta.tsx"   # ∥
Task: "T005 Crear carga.tsx"      # ∥

# Desarrollador B (backend, sin esperar a A):
Task: "T011 test_auth_entry.py (test-first)"
Task: "T017 test_portal_read_only.py (test-first)"
```

## Implementation Strategy

### MVP First (US1)

1. Phase 1 → Phase 2 → Phase 3 (US1)
2. **STOP y VALIDAR**: pantallas separadas con flujo 009 intacto → demo
3. Continuar con US2 (puente con contexto), US4 (puerta y menú propios) y US3 (segregación de servicios), validando cada checkpoint

### Incremental Delivery

Cada story es desplegable por separado: US1 entrega la separación visible; US2 la agilidad del flujo; US4 la separación de entrada/menú; US3 la garantía verificable en servicios. Ninguna rompe a las anteriores (URLs de API estables, reglas de negocio intactas).

## Notes

- Sin migraciones de BD en ninguna tarea (plan.md)
- Las suites de 009 son el arnés de regresión permanente: correrlas tras cada checkpoint
- Commit después de cada tarea o grupo lógico
