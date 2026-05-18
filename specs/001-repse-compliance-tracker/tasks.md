---
description: "Task list for 001-repse-compliance-tracker (core compliance vault)"
---

# Tasks: Bóveda de Cumplimiento REPSE (Core)

**Input**: Design documents from `/specs/001-repse-compliance-tracker/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: La constitución del proyecto exige test-first para rutas críticas (autenticación, autorización, aislamiento multi-tenant, cálculo de cumplimiento). Esos tests se incluyen como **obligatorios** (no opcionales). Tests UI/E2E adicionales son opcionales.

**Organization**: Tareas agrupadas por user story para entrega independiente.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: paralelizable (archivo distinto, sin dependencias).
- **[Story]**: US1 o US2 cuando aplica.
- Rutas exactas en la descripción.

## Path Conventions

Monorepo: `backend/` (FastAPI + SQLAlchemy + Alembic), `frontend/` (Vite + React + TypeScript + Tailwind), `ops/` (Docker Compose + Caddy + scripts). Tests dentro de cada paquete.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: scaffolding inicial del monorepo. Termina con `docker compose up` arrancando una app vacía respondiendo `/health`.

- [X] T001 Crear estructura de monorepo: `backend/`, `frontend/`, `ops/`, `.gitignore`, `README.md` en raíz.
- [X] T002 [P] Inicializar backend Python con `uv` o Poetry en [backend/pyproject.toml](backend/pyproject.toml) declarando deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2.0`, `alembic`, `pymysql`, `pydantic>=2`, `pydantic-settings`, `authlib`, `itsdangerous`, `python-multipart`, `pytesseract`, `pdf2image`, `structlog`, `slowapi`, `prometheus-client`, `sentry-sdk`.
- [X] T003 [P] Inicializar frontend con Vite + React + TS en [frontend/package.json](frontend/package.json) declarando deps: `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `tailwindcss`, `@headlessui/react`, `lucide-react`, `react-hook-form`, `zod`.
- [X] T004 [P] Configurar Tailwind con tokens de la paleta REPSE (azules profundos + neutros + acentos de estado) en [frontend/tailwind.config.ts](frontend/tailwind.config.ts) y [frontend/src/styles/globals.css](frontend/src/styles/globals.css) (FR-016 del spec).
- [X] T005 [P] Configurar lint + format backend: `ruff`, `mypy --strict`, `pytest` en [backend/pyproject.toml](backend/pyproject.toml).
- [X] T006 [P] Configurar lint + format frontend: ESLint, Prettier, TypeScript strict en [frontend/tsconfig.json](frontend/tsconfig.json) y [frontend/eslint.config.js](frontend/eslint.config.js).
- [X] T007 Crear [ops/docker-compose.yml](ops/docker-compose.yml) con servicios `app` (backend), `frontend` (vite dev), `mysql` (8.0), `caddy` (reverse proxy). Volumen persistente `mysql_data` y `uploads`.
- [X] T008 [P] Crear [ops/Caddyfile](ops/Caddyfile) con `tls internal`, proxy `/api/*` → `app:8000`, proxy `/` → `frontend:5173` (dev) o estáticos buildeados (prod).
- [X] T009 [P] Crear [ops/.env.example](ops/.env.example) documentando todas las variables del [quickstart.md](./quickstart.md).
- [X] T010 Crear endpoint trivial `GET /health` en [backend/src/repse/main.py](backend/src/repse/main.py) que retorna `{"status":"ok"}` para validar el stack arrancando.

**Checkpoint**: `docker compose up` levanta la app, `curl https://localhost/api/health` responde 200, frontend monta vacío.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestructura compartida que TODA user story consume. Sin esto, ningún FR del 001 funciona.

**⚠️ CRITICAL**: ninguna user story puede empezar hasta cerrar esta fase.

- [X] T011 Crear configuración Pydantic Settings en [backend/src/repse/config.py](backend/src/repse/config.py) cargando todas las variables de entorno del [quickstart.md](./quickstart.md) (DB, OIDC, APP_SECRET, UPLOAD_ROOT, TESSERACT_LANG, SENTRY_DSN).
- [X] T012 [P] Configurar structlog (JSON renderer, request_id/tenant_id/user_id context) en [backend/src/repse/logging.py](backend/src/repse/logging.py).
- [X] T013 [P] Setup global de Sentry/GlitchTip (opt-in vía `SENTRY_DSN` vacío = deshabilitado) en [backend/src/repse/main.py](backend/src/repse/main.py).
- [X] T014 Crear SQLAlchemy `DeclarativeBase` con naming convention determinista (research.md §2) en [backend/src/repse/db/base.py](backend/src/repse/db/base.py).
- [X] T015 Crear session factory + async/sync engine + dependency `get_db` en [backend/src/repse/db/session.py](backend/src/repse/db/session.py).
- [X] T016 Implementar mixin `TenantOwned` + event listener `before_compile` que inyecta `WHERE organization_id = :current_tenant_id` (research.md §2) en [backend/src/repse/db/tenant_filter.py](backend/src/repse/db/tenant_filter.py).
- [X] T017 Inicializar Alembic + configurar `env.py` para descubrir todos los modelos del paquete `repse.*` en [backend/alembic.ini](backend/alembic.ini), [backend/alembic/env.py](backend/alembic/env.py), [backend/alembic/script.py.mako](backend/alembic/script.py.mako).
- [X] T018 [P] Implementar middleware de request ID + structlog binding en [backend/src/repse/middleware/request_context.py](backend/src/repse/middleware/request_context.py).
- [X] T019 [P] Implementar rate limiting con `slowapi` (10 req/min para auth callback, 60/min para uploads) en [backend/src/repse/middleware/rate_limit.py](backend/src/repse/middleware/rate_limit.py).
- [X] T020 [P] Implementar envelope de errores `{"error": {"code", "message", "details"}}` y exception handler global en [backend/src/repse/errors.py](backend/src/repse/errors.py).
- [X] T021 [P] Implementar `FileStore` con backend `LocalDisk` + tokens JWS firmados con `itsdangerous` (TTL 5 min, validan organization_id) en [backend/src/repse/documents/storage.py](backend/src/repse/documents/storage.py).
- [X] T022 [P] Implementar wrapper de Tesseract OCR con `pytesseract` + `pdf2image` (regex de RFC + fechas en español) en [backend/src/repse/documents/ocr.py](backend/src/repse/documents/ocr.py).
- [X] T023 [P] Implementar calculadora de vencimiento `compute_due_date(coverage_period, periodicity)` con reglas SAT/IMSS (research.md §3) en [backend/src/repse/documents/expiration.py](backend/src/repse/documents/expiration.py).
- [X] T024 Implementar bootstrap de catálogo canónico de `DocumentType` (research.md §9) como migration data-only en [backend/alembic/versions/0002_seed_canonical_doc_types.py](backend/alembic/versions/0002_seed_canonical_doc_types.py).
- [X] T025 Implementar provisioning de Organization: crea `SupplierType` "Sin clasificar" (`origin='system'`) + siembra `SupplierTypeDocumentRequirement` para todos los `DocumentType` canónicos activos (FR-013 del spec 003) en [backend/src/repse/supplier_types/provisioning.py](backend/src/repse/supplier_types/provisioning.py).
- [X] T026 Implementar clients OIDC (Google + Microsoft) con `Authlib` en [backend/src/repse/auth/oidc.py](backend/src/repse/auth/oidc.py).
- [X] T027 Implementar gestión de sesión + cookie firmada con `itsdangerous` en [backend/src/repse/auth/session.py](backend/src/repse/auth/session.py).
- [X] T028 Implementar dependencies `current_user`, `current_tenant`, `require_role(*roles)` en [backend/src/repse/auth/dependencies.py](backend/src/repse/auth/dependencies.py).
- [X] T029 [P] Implementar servicio de bitácora `audit_log.write(action, entity_type, entity_id, metadata)` + helper para acciones del sistema (`actor_user_id=NULL`) en [backend/src/repse/audit/service.py](backend/src/repse/audit/service.py).
- [X] T030 [P] Implementar endpoint `/metrics` con `prometheus_client` (request_count, latency_histogram, error_rate) en [backend/src/repse/observability/metrics.py](backend/src/repse/observability/metrics.py).
- [X] T031 [P] Frontend: configurar React Router + Tanstack Query + AuthProvider + ThemeProvider en [frontend/src/app/providers.tsx](frontend/src/app/providers.tsx) y [frontend/src/app/router.tsx](frontend/src/app/router.tsx).
- [X] T032 [P] Frontend: implementar fetch wrapper con manejo de cookies de sesión, errores y refresco automático en [frontend/src/lib/api.ts](frontend/src/lib/api.ts).
- [X] T033 [P] Frontend: componentes UI primitivos (`Button`, `Card`, `Badge`, `Table`, `Modal`, `Tabs`, `FormField`) en [frontend/src/components/ui/](frontend/src/components/ui/).

**Checkpoint**: capa de datos lista, OIDC conectable, multi-tenant filter activo, OCR/expiration/file storage probables; user stories pueden empezar.

---

## Phase 3: User Story 1 — Registrar proveedores y subir documentos (Priority: P1) 🎯 MVP

**Goal**: un administrador autenticado registra un proveedor (con tipo asignable, default "Sin clasificar"), sube un PDF asociado a un `DocumentType` y lo ve en el listado con su tipo, periodo, fecha de carga y bloque de auditoría "Agregado por".

**Independent Test**: ver [quickstart.md](./quickstart.md#smoke-test-us1--us2). Login OAuth (mock) → POST `/api/v1/suppliers` → POST `/api/v1/suppliers/{id}/documents` con un PDF → GET `/api/v1/suppliers/{id}` muestra el documento con su estado y `audit.added`.

### Tests obligatorios (rutas críticas: auth + multi-tenant + upload)

> **NOTE**: estos tests se escriben PRIMERO y deben fallar antes de implementar (constitución, principio III).

- [X] T034 [P] [US1] Contract test: `POST /api/v1/auth/callback/{provider}` valida `state`, emite cookie de sesión y persiste user/organization en [backend/tests/contract/test_auth_contract.py](backend/tests/contract/test_auth_contract.py).
- [X] T035 [P] [US1] Contract test: `GET /api/v1/auth/me` retorna 401 sin sesión y perfil con `organization` con sesión en [backend/tests/contract/test_auth_contract.py](backend/tests/contract/test_auth_contract.py).
- [X] T036 [P] [US1] Contract test: `POST /api/v1/suppliers` valida payload, asigna "Sin clasificar" si falta `supplier_type_id`, rechaza RFC duplicado por org (`409 rfc_exists`) en [backend/tests/contract/test_suppliers_contract.py](backend/tests/contract/test_suppliers_contract.py).
- [X] T037 [P] [US1] Contract test: `POST /api/v1/suppliers/{id}/documents` acepta multipart con PDF, valida tipo activo, computa `due_date_calculated`, registra `audit.added` en [backend/tests/contract/test_documents_contract.py](backend/tests/contract/test_documents_contract.py).
- [X] T038 [P] [US1] Integration test multi-tenant negativo: org A no puede GET/POST documentos de org B (responde 404 nunca 403) en [backend/tests/integration/test_tenant_isolation.py](backend/tests/integration/test_tenant_isolation.py).
- [X] T039 [P] [US1] Integration test: subir un duplicado exacto (mismo sha256) en el mismo tenant responde `409 duplicate_file` con `id` del existente en [backend/tests/integration/test_documents_upload.py](backend/tests/integration/test_documents_upload.py).

### Models (paralelos, archivos distintos)

- [X] T040 [P] [US1] Modelo `Organization` con columnas y enum `status` (active/grace/deleted) en [backend/src/repse/organizations/models.py](backend/src/repse/organizations/models.py).
- [X] T041 [P] [US1] Modelo `User` con `oidc_subject`, `oidc_provider`, `role`, mixin `TenantOwned` en [backend/src/repse/users/models.py](backend/src/repse/users/models.py).
- [X] T042 [P] [US1] Modelo `SupplierType` con `origin` (system/custom), `status` (active/archived), `TenantOwned` en [backend/src/repse/supplier_types/models.py](backend/src/repse/supplier_types/models.py).
- [X] T043 [P] [US1] Modelo `SupplierTypeDocumentRequirement` con `periodicity_override`, `status` (active/retired), FK a `SupplierType` y `DocumentType` en [backend/src/repse/supplier_types/models.py](backend/src/repse/supplier_types/models.py).
- [X] T044 [P] [US1] Modelo `DocumentType` con `slug`, `periodicity`, `origin` (canonical/custom), `organization_id` nullable (canónicos NULL) en [backend/src/repse/document_types/models.py](backend/src/repse/document_types/models.py).
- [X] T045 [P] [US1] Modelo `TenantDocumentTypeSetting` (activación canónico por tenant) en [backend/src/repse/document_types/models.py](backend/src/repse/document_types/models.py).
- [X] T046 [P] [US1] Modelo `Supplier` con FK `supplier_type_id` NOT NULL, `TenantOwned` en [backend/src/repse/suppliers/models.py](backend/src/repse/suppliers/models.py).
- [X] T047 [P] [US1] Modelo `Document` con todas las columnas del data-model: `due_date_calculated`, `due_date_effective`, `verified*`, `last_updated_*`, `ocr_*`, `version`, `is_latest`, `TenantOwned` en [backend/src/repse/documents/models.py](backend/src/repse/documents/models.py).
- [X] T048 [P] [US1] Modelo `AuditLog` append-only en [backend/src/repse/audit/models.py](backend/src/repse/audit/models.py).
- [X] T049 [US1] Migration Alembic `0001_baseline.py` que crea todas las tablas anteriores con índices del data-model (`uq_*`, `ix_*`) en [backend/alembic/versions/0001_baseline.py](backend/alembic/versions/0001_baseline.py).

### Pydantic schemas

- [X] T050 [P] [US1] Schemas Pydantic para Organization (`OrganizationOut`, `OrganizationPatch`) en [backend/src/repse/organizations/schemas.py](backend/src/repse/organizations/schemas.py).
- [X] T051 [P] [US1] Schemas para User (`UserOut`, `UserCreate`, `UserPatch`) en [backend/src/repse/users/schemas.py](backend/src/repse/users/schemas.py).
- [X] T052 [P] [US1] Schemas para SupplierType (`SupplierTypeOut`, `SupplierTypeListItem`) en [backend/src/repse/supplier_types/schemas.py](backend/src/repse/supplier_types/schemas.py).
- [X] T053 [P] [US1] Schemas para DocumentType (`DocumentTypeOut`) en [backend/src/repse/document_types/schemas.py](backend/src/repse/document_types/schemas.py).
- [X] T054 [P] [US1] Schemas para Supplier (`SupplierIn`, `SupplierOut`, `SupplierDetailOut` con `documents_by_type`, `SupplierPatch`) en [backend/src/repse/suppliers/schemas.py](backend/src/repse/suppliers/schemas.py).
- [X] T055 [P] [US1] Schemas para Document (`DocumentOut` con bloque `audit` `{added, last_updated, validated}`, `DocumentUploadIn`) en [backend/src/repse/documents/schemas.py](backend/src/repse/documents/schemas.py).

### Auth endpoints

- [X] T056 [US1] Endpoint `GET /api/v1/auth/login/{provider}` (Google/Microsoft) en [backend/src/repse/auth/routes.py](backend/src/repse/auth/routes.py).
- [X] T057 [US1] Endpoint `GET /api/v1/auth/callback/{provider}`: valida state, crea/recupera User, dispara provisioning Organization si es primer login (T025), emite cookie sesión en [backend/src/repse/auth/routes.py](backend/src/repse/auth/routes.py).
- [X] T058 [US1] Endpoint `POST /api/v1/auth/logout` invalida cookie en [backend/src/repse/auth/routes.py](backend/src/repse/auth/routes.py).
- [X] T059 [US1] Endpoint `GET /api/v1/auth/me` retorna perfil + organization en [backend/src/repse/auth/routes.py](backend/src/repse/auth/routes.py).

### Organization & users endpoints

- [X] T060 [P] [US1] Endpoint `GET /api/v1/organization` y `PATCH /api/v1/organization` (admin only) en [backend/src/repse/organizations/routes.py](backend/src/repse/organizations/routes.py).
- [X] T061 [P] [US1] Endpoints CRUD `GET/POST/PATCH/DELETE /api/v1/users` con regla "no dejar al tenant sin admins" (409 `last_admin`) en [backend/src/repse/users/routes.py](backend/src/repse/users/routes.py).

### SupplierType endpoints (solo lectura, escritura en spec 003)

- [X] T062 [P] [US1] Endpoint `GET /api/v1/supplier-types` (lista del tenant) en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).
- [X] T063 [P] [US1] Endpoint `GET /api/v1/supplier-types/{id}` (con `include_requirements`) en [backend/src/repse/supplier_types/routes.py](backend/src/repse/supplier_types/routes.py).

### DocumentType endpoints

- [X] T064 [P] [US1] Endpoints `GET /api/v1/document-types` y `GET /api/v1/document-types/{id}` (lectura, filtrando activos por defecto) en [backend/src/repse/document_types/routes.py](backend/src/repse/document_types/routes.py).

### Supplier CRUD

- [X] T065 [US1] Servicio `suppliers.service`: crear (asigna "Sin clasificar" si falta `supplier_type_id`), validar RFC único por org, registrar audit log, recalcular cumplimiento al cambiar tipo (FR-005a) en [backend/src/repse/suppliers/service.py](backend/src/repse/suppliers/service.py).
- [X] T066 [US1] Endpoint `POST /api/v1/suppliers` en [backend/src/repse/suppliers/routes.py](backend/src/repse/suppliers/routes.py).
- [X] T067 [US1] Endpoint `GET /api/v1/suppliers` con filtros (`q`, `status`, `supplier_type_id`, `sort`) y paginación cursor-based en [backend/src/repse/suppliers/routes.py](backend/src/repse/suppliers/routes.py).
- [X] T068 [US1] Endpoint `GET /api/v1/suppliers/{id}` que devuelve `SupplierDetailOut` con `documents_by_type` (resolviendo requirements según `SupplierType` + último Document por tipo+periodo) en [backend/src/repse/suppliers/routes.py](backend/src/repse/suppliers/routes.py).
- [X] T069 [US1] Endpoint `PATCH /api/v1/suppliers/{id}` (cambio de tipo dispara recálculo) en [backend/src/repse/suppliers/routes.py](backend/src/repse/suppliers/routes.py).
- [X] T070 [US1] Endpoints `DELETE /api/v1/suppliers/{id}` (soft-delete) y `POST /api/v1/suppliers/{id}/reactivate` en [backend/src/repse/suppliers/routes.py](backend/src/repse/suppliers/routes.py).

### Document upload

- [X] T071 [US1] Servicio `documents.upload`: orquesta validación de mime/tamaño, dedup por sha256, cálculo de `due_date_calculated`, override manual, versioning (`is_latest`), audit log, llamada async/sync a OCR (research.md §4) en [backend/src/repse/documents/service.py](backend/src/repse/documents/service.py).
- [X] T072 [US1] Endpoint `POST /api/v1/suppliers/{id}/documents` (multipart/form-data) en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [X] T073 [US1] Endpoint `GET /api/v1/documents` con filtros y paginación en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [X] T074 [US1] Endpoint `GET /api/v1/documents/{id}` con bloque `audit` poblado en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [X] T075 [US1] Endpoint `POST /api/v1/documents/{id}/download-token` emite JWS firmado (TTL 5 min) en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [X] T076 [US1] Endpoint `GET /api/v1/files/{token}` valida firma + sesión + tenant match, sirve `StreamingResponse` con `Content-Disposition` en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).

### Frontend US1

- [X] T077 [P] [US1] Página de login con botones "Continuar con Google" / "Continuar con Microsoft" en [frontend/src/pages/auth/login.tsx](frontend/src/pages/auth/login.tsx).
- [X] T078 [P] [US1] App shell con sidebar (Proveedores, Tablero placeholder, Configuración) y header con perfil en [frontend/src/app/layout.tsx](frontend/src/app/layout.tsx).
- [X] T079 [US1] Hook + queries Tanstack para `suppliers`, `supplier-types`, `document-types`, `documents` en [frontend/src/lib/api/index.ts](frontend/src/lib/api/index.ts).
- [X] T080 [P] [US1] Página listado de proveedores con búsqueda, filtros (estado, tipo de proveedor) y paginación en [frontend/src/pages/suppliers/list.tsx](frontend/src/pages/suppliers/list.tsx).
- [X] T081 [P] [US1] Formulario "Nuevo proveedor" con selector de `SupplierType` (incluye "Sin clasificar") y validación zod en [frontend/src/pages/suppliers/new.tsx](frontend/src/pages/suppliers/new.tsx).
- [X] T082 [P] [US1] Página detalle del proveedor con resumen + tabla `documents_by_type` (requeridos según tipo) en [frontend/src/pages/suppliers/detail.tsx](frontend/src/pages/suppliers/detail.tsx).
- [X] T083 [P] [US1] Modal "Subir documento": selector de tipo, periodo cubierto, override opcional de vencimiento, drag-drop, render de OCR best-effort prellenado, en [frontend/src/components/documents/UploadDialog.tsx](frontend/src/components/documents/UploadDialog.tsx).
- [X] T084 [P] [US1] Componente `<AuditBlock>` que muestra "Agregado por / Última actualización / Validado" (FR-011c, FR-011d) en [frontend/src/components/documents/AuditBlock.tsx](frontend/src/components/documents/AuditBlock.tsx).
- [X] T085 [P] [US1] Componente `<DocumentRow>` con tooltip de auditoría on-hover (FR-011c) en [frontend/src/components/documents/DocumentRow.tsx](frontend/src/components/documents/DocumentRow.tsx).
- [X] T086 [P] [US1] E2E Playwright smoke US1 (login mock OIDC → crear proveedor → subir PDF → ver en lista con audit block) en [frontend/tests/e2e/us1_upload_flow.spec.ts](frontend/tests/e2e/us1_upload_flow.spec.ts).

### Addendum US1: cambio destructivo de `SupplierType` (FR-005b / FR-005c / FR-005d, escenarios 1c–1g)

> Incremento sobre el endpoint existente T069 (`PATCH /api/v1/suppliers/{id}`): cuando el `supplier_type_id` cambia y hay documentos del proveedor cuya `effective_due_date` cae en el año natural en curso (zona horaria del tenant), el cambio se bloquea hasta que el usuario confirme la eliminación destructiva escribiendo `eliminar` en un popup. Confirmar elimina permanentemente esos documentos, aplica el nuevo tipo, recalcula requisitos y deja audit log, todo transaccional.

#### Tests obligatorios (rutas críticas: borrado destructivo + multi-tenant)

- [ ] T117 [P] [US1] Contract test: `GET /api/v1/suppliers/{id}/type-change-preview?supplier_type_id=X` retorna `{requires_confirmation, affected_count, affected_documents:[{id,document_type,coverage_period,due_date_effective}]}`; con tenant ajeno responde 404 en [backend/tests/contract/test_suppliers_type_change_contract.py](backend/tests/contract/test_suppliers_type_change_contract.py).
- [ ] T118 [P] [US1] Contract test: `PATCH /api/v1/suppliers/{id}` con nuevo `supplier_type_id` y docs en año en curso SIN `confirmation_text` responde `409 confirmation_required` con `affected_documents` en el envelope `error.details`; sin docs en año en curso aplica el cambio directo (200) en [backend/tests/contract/test_suppliers_type_change_contract.py](backend/tests/contract/test_suppliers_type_change_contract.py).
- [ ] T119 [P] [US1] Contract test: `PATCH /api/v1/suppliers/{id}` con `confirmation_text` válido (`"eliminar"`, comparación case-insensitive, trimming) elimina los documentos afectados, aplica el nuevo tipo, recalcula `compliance` y retorna 200; con `confirmation_text` incorrecto responde `422 invalid_confirmation` en [backend/tests/contract/test_suppliers_type_change_contract.py](backend/tests/contract/test_suppliers_type_change_contract.py).
- [ ] T120 [P] [US1] Integration test: si el borrado físico de un archivo falla a mitad de la transacción, la operación se revierte completamente — el `supplier_type_id` original se conserva, ningún `Document` queda eliminado y no quedan archivos huérfanos en `UPLOAD_ROOT` en [backend/tests/integration/test_supplier_type_change_rollback.py](backend/tests/integration/test_supplier_type_change_rollback.py).
- [ ] T121 [P] [US1] Integration test: confirmar elimina también versiones históricas archivadas (`is_latest=false`) cuya `effective_due_date` cae en el año en curso, y respeta documentos sin vigencia (NULL) o con vencimiento fuera del año en curso en [backend/tests/integration/test_supplier_type_change_scope.py](backend/tests/integration/test_supplier_type_change_scope.py).
- [ ] T122 [P] [US1] Integration test: tras confirmar, `audit_log` contiene un registro `document.deleted_by_supplier_type_change` por cada documento eliminado (con metadatos del tipo anterior y nuevo) y un registro `supplier.type_changed` para el proveedor en [backend/tests/integration/test_supplier_type_change_audit.py](backend/tests/integration/test_supplier_type_change_audit.py).

#### Backend

- [ ] T123 [US1] Servicio `suppliers.type_change_service.preview_destructive_change(supplier_id, new_supplier_type_id)` que evalúa documentos con `effective_due_date` dentro del año en curso (basado en `Organization.timezone`) y devuelve `{requires_confirmation, affected_count, affected_documents}` en [backend/src/repse/suppliers/type_change_service.py](backend/src/repse/suppliers/type_change_service.py).
- [ ] T124 [US1] Servicio `suppliers.type_change_service.execute_destructive_change(supplier_id, new_supplier_type_id, actor)` transaccional: (a) hard-delete de los documentos afectados (registro + archivo físico vía `FileStore.delete`), (b) actualiza `Supplier.supplier_type_id`, (c) invoca `documents.recalculator.recalc_for_supplier`, (d) escribe `audit_log` por cada borrado y por el cambio de tipo; rollback completo ante cualquier fallo en [backend/src/repse/suppliers/type_change_service.py](backend/src/repse/suppliers/type_change_service.py).
- [ ] T125 [US1] Actualizar `SupplierPatch` (T054) para aceptar campo opcional `confirmation_text: str | None`; añadir schema `SupplierTypeChangePreviewOut` y `AffectedDocumentOut` en [backend/src/repse/suppliers/schemas.py](backend/src/repse/suppliers/schemas.py).
- [ ] T126 [US1] Endpoint `GET /api/v1/suppliers/{id}/type-change-preview` que valida tenant + permiso (`admin` o `manager`) y delega a `preview_destructive_change` en [backend/src/repse/suppliers/routes.py](backend/src/repse/suppliers/routes.py).
- [ ] T127 [US1] Actualizar `PATCH /api/v1/suppliers/{id}` (T069) para detectar cambio de `supplier_type_id`: si `requires_confirmation` y falta `confirmation_text` retorna `409 confirmation_required` con `affected_documents` en `error.details`; si el `confirmation_text` no coincide (case-insensitive, trim) con `"eliminar"` retorna `422 invalid_confirmation`; si coincide delega a `execute_destructive_change` en [backend/src/repse/suppliers/routes.py](backend/src/repse/suppliers/routes.py).
- [ ] T128 [US1] Registrar las acciones `document.deleted_by_supplier_type_change` y (si no existía) `supplier.type_changed` en el enum/registro de acciones de auditoría en [backend/src/repse/audit/actions.py](backend/src/repse/audit/actions.py).
- [ ] T129 [US1] Actualizar contrato OpenAPI/markdown de proveedores: documentar `GET /suppliers/{id}/type-change-preview`, el nuevo campo `confirmation_text` en `PATCH /suppliers/{id}` y los códigos `409 confirmation_required` / `422 invalid_confirmation` en [specs/001-repse-compliance-tracker/contracts/suppliers.md](specs/001-repse-compliance-tracker/contracts/suppliers.md).

#### Frontend

- [ ] T130 [P] [US1] Componente reutilizable `<DestructiveConfirmDialog>` que muestra el conteo y resumen de elementos a eliminar, una caja de texto que exige escribir `eliminar` (case-insensitive, trim) y un botón de confirmación habilitado solo cuando coincide; botón cancelar siempre habilitado en [frontend/src/components/ui/DestructiveConfirmDialog.tsx](frontend/src/components/ui/DestructiveConfirmDialog.tsx).
- [ ] T131 [P] [US1] Hook `useSupplierTypeChangePreview(supplierId, newTypeId)` y mutación `useChangeSupplierType` (Tanstack Query) que envuelven los endpoints nuevos en [frontend/src/lib/api/suppliers.ts](frontend/src/lib/api/suppliers.ts).
- [ ] T132 [P] [US1] Integración del flujo en el formulario de edición del proveedor (T082): al cambiar `supplier_type_id`, pre-consulta `type-change-preview`; si `requires_confirmation`, abre `<DestructiveConfirmDialog>` con la lista de documentos; al confirmar, envía `PATCH` con `confirmation_text`; manejo de errores `409`/`422` mostrando feedback claro en [frontend/src/pages/suppliers/edit.tsx](frontend/src/pages/suppliers/edit.tsx).
- [ ] T133 [P] [US1] E2E Playwright: editar un proveedor con docs cuya `effective_due_date` cae en el año en curso → cambiar tipo → ver popup → escribir `eliminar` → confirmar → assert: documentos eliminados, nuevo tipo aplicado, agregado de cumplimiento recalculado; flujo cancelar deja todo intacto en [frontend/tests/e2e/us1_destructive_type_change.spec.ts](frontend/tests/e2e/us1_destructive_type_change.spec.ts).
- [ ] T134 [P] [US1] E2E Playwright camino feliz sin destrucción: editar proveedor SIN docs en año en curso → cambiar tipo → assert: aplica directo sin popup, requisitos recalculados en [frontend/tests/e2e/us1_type_change_no_docs.spec.ts](frontend/tests/e2e/us1_type_change_no_docs.spec.ts).

**Checkpoint addendum**: el cambio de `SupplierType` desde la pantalla de edición exige confirmación destructiva (texto `eliminar`) cuando hay documentos del año en curso, elimina solo esos documentos en transacción atómica, aplica el nuevo tipo y recalcula requisitos; si no hay documentos afectados, el cambio se aplica directo. Auditoría completa en `audit_log`.

**Checkpoint**: US1 funcional. Un usuario puede registrarse vía Google/Microsoft, crear un proveedor, subir un PDF y verlo en el detalle con su audit trail "Agregado por".

---

## Phase 4: User Story 2 — Visualizar el estado de cumplimiento por proveedor (Priority: P1)

**Goal**: el detalle de un proveedor muestra cada documento con su estado (vigente / por vencer / vencido / faltante), un indicador agregado y un tablero general del tenant con conteos. La verificación manual ("validado por") y el tab "Historial" están disponibles.

**Independent Test**: con un proveedor que tiene documentos en distintos estados (sembrados por fixture), abrir el detalle ve cada uno con su badge correcto, el % de cumplimiento agregado coincide con el cálculo manual, y el badge "Verificado" aparece cuando se ejecuta `POST /documents/{id}/verify`.

### Tests obligatorios

- [ ] T087 [P] [US2] Integration test: cálculo de estado (vigente/por_vencer/vencido) respeta `expiring_soon_threshold_days` por organización y dispara recálculo al cambiarlo (FR-013) en [backend/tests/integration/test_status_calculation.py](backend/tests/integration/test_status_calculation.py).
- [ ] T088 [P] [US2] Integration test: "Faltante" se deriva de `SupplierType` requirements, no del catálogo global (FR-012b) en [backend/tests/integration/test_compliance_aggregate.py](backend/tests/integration/test_compliance_aggregate.py).
- [ ] T089 [P] [US2] Contract test: `POST /documents/{id}/verify` registra `verified_by`, `verified_at`, `verified_note` y actualiza `last_updated_by/_at`; `POST /documents/{id}/unverify` invierte (auditado) en [backend/tests/contract/test_documents_verify_contract.py](backend/tests/contract/test_documents_verify_contract.py).
- [ ] T090 [P] [US2] Contract test: `GET /documents/{id}/history` retorna timeline humano + sistema (acciones del sistema con `actor.type='system'`) en [backend/tests/contract/test_documents_history_contract.py](backend/tests/contract/test_documents_history_contract.py).

### Servicios y cálculos

- [ ] T091 [US2] Servicio `documents.status_calculator.compute_status(document, today, threshold_days)` con la regla del data-model (vigente/expiring_soon/expired) en [backend/src/repse/documents/status.py](backend/src/repse/documents/status.py).
- [ ] T092 [US2] Servicio `documents.recalculator.recalc_for_organization(org_id)` que materializa `status` en todos los documentos del tenant; idempotente; usado por (a) cron diario, (b) cambio de threshold, (c) cambio de `supplier_type_id`, (d) edición de requirements en [backend/src/repse/documents/recalculator.py](backend/src/repse/documents/recalculator.py).
- [ ] T093 [US2] Cron / scheduler diario que invoca `recalc_for_organization` para cada org activa (FastAPI BackgroundTask al startup + APScheduler simple) en [backend/src/repse/documents/jobs.py](backend/src/repse/documents/jobs.py).
- [ ] T094 [US2] Servicio `suppliers.compliance.aggregate(supplier_id)` que devuelve `{percent, counts {valid, expiring_soon, expired, missing}}` derivando "missing" de `SupplierType.requirements` − Documents.is_latest=true por periodo en [backend/src/repse/suppliers/compliance.py](backend/src/repse/suppliers/compliance.py).
- [ ] T095 [US2] Ajustar `SupplierDetailOut` (T054) para incluir el agregado y, para cada requirement faltante, una fila "Faltante" sintética con su tipo + periodo esperado.

### Verification & history endpoints

- [ ] T096 [US2] Endpoint `POST /api/v1/documents/{id}/verify`: bumpea `verified*` + `last_updated_*`, registra audit log `document.verified` en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [ ] T097 [US2] Endpoint `POST /api/v1/documents/{id}/unverify` (admin only) en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [ ] T098 [US2] Endpoint `DELETE /api/v1/documents/{id}` con ventana de gracia configurable (default 24 h) (`409 delete_window_expired`) en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [ ] T099 [US2] Endpoint `GET /api/v1/documents/{id}/history` que consulta `audit_log` filtrado por `entity_type='document'`, mapea acciones humanas/sistema al esquema del contrato en [backend/src/repse/documents/routes.py](backend/src/repse/documents/routes.py).
- [ ] T100 [US2] Endpoint `GET /api/v1/audit-log` (lectura genérica para admin/manager) en [backend/src/repse/audit/routes.py](backend/src/repse/audit/routes.py).

### Frontend US2

- [ ] T101 [P] [US2] Componente `<ComplianceBadge status>` con paleta de la constitución FR-016 (verde/ámbar/rojo/gris para estados) en [frontend/src/components/documents/ComplianceBadge.tsx](frontend/src/components/documents/ComplianceBadge.tsx).
- [ ] T102 [P] [US2] Componente `<ComplianceSummary>` para el header del detalle de proveedor (porcentaje + barras de conteo) en [frontend/src/components/suppliers/ComplianceSummary.tsx](frontend/src/components/suppliers/ComplianceSummary.tsx).
- [ ] T103 [P] [US2] Tab "Historial" en detalle del documento, consume `/documents/{id}/history` y renderiza acciones humanas vs sistema con etiquetas distintas en [frontend/src/components/documents/HistoryTab.tsx](frontend/src/components/documents/HistoryTab.tsx).
- [ ] T104 [P] [US2] Botón "Marcar como verificado" + modal con campo `note` en el detalle del documento en [frontend/src/components/documents/VerifyDialog.tsx](frontend/src/components/documents/VerifyDialog.tsx).
- [ ] T105 [P] [US2] Página "Tablero" minimal del tenant: 4 cards con totales (proveedores activos, % cumplimiento global, en riesgo, por vencer 30 d). Sin gráficos (eso es spec 005). En [frontend/src/pages/dashboard/index.tsx](frontend/src/pages/dashboard/index.tsx).
- [ ] T106 [P] [US2] E2E Playwright US2: tenant con datos sembrados → abrir detalle de proveedor → ver estados correctos → marcar verificado → ver badge "Verificado" en [frontend/tests/e2e/us2_compliance_view.spec.ts](frontend/tests/e2e/us2_compliance_view.spec.ts).

**Checkpoint**: US1 + US2 completas. Un usuario puede gestionar proveedores, cargar documentos, ver estado de cumplimiento por proveedor y por tenant, marcar verificación y consultar el historial completo de un documento.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: hardening, observabilidad, operación on-prem y validación final.

- [ ] T107 [P] Implementar [ops/scripts/backup.sh](ops/scripts/backup.sh) (mysqldump + tar de `var/uploads/`) y [ops/scripts/restore.sh](ops/scripts/restore.sh).
- [ ] T108 [P] Configurar GitHub Actions CI (lint, mypy, pytest, npm test, e2e) en [.github/workflows/ci.yml](.github/workflows/ci.yml).
- [ ] T109 [P] Configurar dependency scanning (pip-audit + npm audit --omit=dev) que bloquee high/critical en [.github/workflows/ci.yml](.github/workflows/ci.yml).
- [ ] T110 [P] Test unitario que verifica que ningún logger emite contraseñas, tokens, payloads completos de auth en [backend/tests/unit/test_logs_redaction.py](backend/tests/unit/test_logs_redaction.py).
- [ ] T111 [P] Test de carga local: 500 proveedores × 50 documentos, GET /suppliers/{id} responde <300 ms p95 (SC-003) en [backend/tests/performance/test_supplier_detail_p95.py](backend/tests/performance/test_supplier_detail_p95.py).
- [ ] T112 [P] Generar OpenAPI desde FastAPI y validar contra contratos en [contracts/](./contracts/) (script de diff) en [backend/tests/contract/test_openapi_matches_contracts.py](backend/tests/contract/test_openapi_matches_contracts.py).
- [ ] T113 [P] Implementar Dockerfile productivo del backend y del frontend en [ops/Dockerfile.app](ops/Dockerfile.app) y [ops/Dockerfile.frontend](ops/Dockerfile.frontend) (multi-stage, no-root user).
- [ ] T114 [P] Implementar [ops/docker-compose.prod.yml](ops/docker-compose.prod.yml) usando los Dockerfiles productivos.
- [ ] T115 Ejecutar el smoke del [quickstart.md](./quickstart.md#smoke-test-us1--us2) en un entorno limpio y dejar evidencia (capturas + log de comandos) en [docs/smoke-2026-05-17.md](docs/smoke-2026-05-17.md).
- [ ] T116 Documentación operativa breve (`docs/operations.md`): rotación de logs, política de backups, recuperación, rotación de `APP_SECRET`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: sin dependencias.
- **Phase 2 (Foundational)**: depende de Phase 1.
- **Phase 3 (US1)**: depende de Phase 2.
- **Phase 4 (US2)**: depende de Phase 2 (puede empezar en paralelo con US1 si el equipo tiene capacidad, **pero** muchas tareas de US2 reutilizan endpoints/UI de US1 — más eficiente terminar US1 primero).
- **Phase 5 (Polish)**: depende de US1 + US2 (al menos demo-listos).

### Critical-path sequencing dentro de Foundational

- T014 → T015 → T016 (DB base + session + tenant filter) son el camino crítico.
- T017 (Alembic) puede correr en paralelo con T011–T013.
- T024 (seed canónico) depende de T017 + T044/T049 (tablas baseline).
- T025 (provisioning Sin clasificar) depende de T024 + T042/T043.
- T026–T028 (OIDC + sesión + deps) deben preceder a cualquier endpoint.

### Critical-path sequencing dentro de US1

- T040–T048 (models) en paralelo → T049 (migration baseline) → T050–T055 (schemas) → T056–T076 (endpoints) → T077–T086 (frontend).
- T071 (servicio de upload) depende de T021 (FileStore) + T022 (OCR) + T023 (expiration) + T047 (Document model).
- T065 (servicio supplier) depende de T025 (provisioning para garantizar "Sin clasificar" existe).
- **Addendum cambio destructivo (T117–T134)**: T123 + T124 (servicio type-change) dependen de T047 (Document model), T021 (FileStore) y T029 (audit service); el agregado de cumplimiento se recomputa lazy en el siguiente GET (T068), no requiere recalculator materializado. T127 modifica el endpoint T069 ya implementado. T132 modifica la página de edición T082. Tests T117–T122 paralelos entre sí; backend T123–T128 secuencial salvo T125 (schemas) y T128 (audit actions) paralelos; frontend T130–T134 paralelos entre sí (archivos distintos).

### Critical-path sequencing dentro de US2

- T091 (status_calculator) → T092 (recalculator) → T094 (aggregate) → T095 (detail enriched).
- T096–T100 (endpoints) dependen de los servicios.
- T101–T106 (frontend) dependen de los endpoints.

### Parallel Opportunities

- Phase 1: T002–T006 todos paralelos (lenguajes/lints distintos).
- Phase 2: T011/T012/T013/T018/T019/T020/T029/T030/T031/T032/T033 paralelos; modelos solo dependen de T014 + T015 + T016.
- Phase 3: dentro de Tests, los T034–T039 todos paralelos. Models T040–T048 paralelos. Schemas T050–T055 paralelos. Frontend T077–T086 paralelos entre sí.
- Phase 4: T087–T090 (tests) paralelos. Frontend T101–T106 paralelos.
- Phase 5: la mayoría son paralelos.

---

## Parallel Example: arranque de US1

```bash
# Tras Phase 2 cerrada, lanza los 6 tests críticos en paralelo:
Task: "T034 [US1] Contract test auth callback"
Task: "T035 [US1] Contract test auth me"
Task: "T036 [US1] Contract test suppliers POST"
Task: "T037 [US1] Contract test documents POST"
Task: "T038 [US1] Integration test tenant isolation"
Task: "T039 [US1] Integration test duplicate file"

# En paralelo, crea los 9 modelos:
Task: "T040 Organization model"
Task: "T041 User model"
Task: "T042 SupplierType model"
Task: "T043 SupplierTypeDocumentRequirement model"
Task: "T044 DocumentType model"
Task: "T045 TenantDocumentTypeSetting model"
Task: "T046 Supplier model"
Task: "T047 Document model"
Task: "T048 AuditLog model"
```

---

## Implementation Strategy

### MVP (US1 únicamente)

1. Phase 1 (Setup): T001–T010.
2. Phase 2 (Foundational): T011–T033.
3. Phase 3 (US1): T034–T086.
4. Validar contra [quickstart.md](./quickstart.md): login OAuth (mock) → crear proveedor → subir PDF → verlo en lista con bloque "Agregado por".
5. Deploy/demo si pasa.

### Incremental delivery

1. Setup + Foundational → infra lista.
2. US1 (P1) → MVP usable.
3. US2 (P1) → producto sin cuya parte "ver estado" no entrega valor de negocio (ambos US son P1; entregar juntos antes de declarar v1).
4. Polish → preparar para clientes piloto.

### Notas operativas

- Antes de US2, ejecutar test E2E negativo de aislamiento multi-tenant (T038) en CI. Bloquea merge si falla.
- Mantener `mypy --strict` y `ruff` verdes desde el primer PR (Phase 1 setup lo activa).
- Cada PR cierra una task o un grupo coherente; el commit message referencia el `TID`.
- Las tareas de spec 003 (admin de catálogos), 002 (alertas), 004 (reportes) y 005 (dashboard) se generan en sus propios `tasks.md` cuando se corra `/speckit-tasks` sobre cada uno.

---

## Notes

- [P] = paralelizable (archivo distinto, sin dependencias inmediatas).
- [Story] mapea a US1 / US2 del [spec.md](./spec.md).
- Cada US debe ser independientemente completable y testeable.
- Los tests marcados como obligatorios cubren las rutas críticas que la constitución exige (auth + multi-tenant + cumplimiento). Otros tests son opcionales pero recomendados.
- Verificar que los tests fallen antes de implementar (rojo → verde → refactor, principio III).
- Commitear tras cada task o grupo coherente.
- Pausar en cada Checkpoint para validar antes de avanzar.
- Evitar: tareas vagas, conflictos del mismo archivo en `[P]`, dependencias cross-story que rompan la independencia de las US.
