---
description: "Task list for 004-compliance-reports"
---

# Tasks: Reportes Exportables de Cumplimiento

**Input**: Design documents from `/specs/004-compliance-reports/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reports-api.md, quickstart.md

**Tests**: INCLUIDOS. La spec exige validación con pruebas automatizadas (SC-001, SC-004, SC-005, SC-006) y la Constitución III obliga tests-first para aislamiento multi-tenant y autorización. Los tests de aislamiento y de descarga se escriben antes de su implementación.

**Organization**: Tareas agrupadas por historia de usuario para implementación y prueba independientes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivos distintos, sin dependencias)
- **[Story]**: Historia de usuario a la que pertenece (US1, US2, US3)
- Rutas exactas incluidas en cada descripción

## Path Conventions

- Backend: `backend/src/repse/reports/`, tests en `backend/tests/{contract,integration,unit}/`
- Frontend: `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicializar el módulo `reports` y declarar dependencias.

- [ ] T001 Crear estructura del módulo backend `backend/src/repse/reports/` con `__init__.py`, y subcarpetas `renderers/` y `templates/` según plan.md
- [ ] T002 Declarar dependencias `weasyprint` y `jinja2` en `backend/pyproject.toml` (o requirements) e instalar en `backend/.venv`
- [ ] T003 [P] Añadir libs nativas de WeasyPrint (Pango/Cairo/GDK-Pixbuf) al `Dockerfile` del backend según quickstart.md
- [ ] T004 [P] Crear `frontend/src/lib/api/reports.ts` con el esqueleto del cliente (tipos de request/response del contrato) sin lógica aún

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura compartida por todas las historias: entidad, configuración, almacenamiento, router y motor de filas.

**⚠️ CRITICAL**: Ninguna historia puede empezar hasta completar esta fase.

- [ ] T005 [US-none] Crear el modelo SQLAlchemy `ExportRequest` en `backend/src/repse/reports/models.py` con todos los campos y enums de data-model.md
- [ ] T006 Crear la migración de base de datos para la tabla `export_request` usando el mecanismo de migraciones del proyecto
- [ ] T007 [P] Definir esquemas Pydantic en `backend/src/repse/reports/schemas.py` (`ExportRequestCreate`, `ExportRequestOut`, filtros, enums de `scope`/`format`/`status`) según contracts/reports-api.md
- [ ] T008 [P] Añadir configuración por entorno en el módulo de settings: `REPORTS_ASYNC_SUPPLIER_THRESHOLD`, `REPORTS_ASYNC_DOCUMENT_THRESHOLD`, `REPORTS_LINK_TTL_HOURS`, `REPORTS_ZIP_MAX_BYTES`, `REPORTS_STORAGE_DIR`, `REPORTS_TENANT_TZ_DEFAULT` (quickstart.md)
- [ ] T009 [P] Implementar el generador de filas del reporte (proyección proveedor × tipo) en `backend/src/repse/reports/service.py` reutilizando el cálculo de estado del módulo `compliance` (FR-005/SC-001), con etiquetado "Faltante" y "tipo inactivo/archivado" (FR-011) y conversión de fechas a zona horaria del tenant con `zoneinfo` (FR-012)
- [ ] T010 Registrar el router `reports` en `backend/src/repse/main.py` bajo el prefijo `/api/reports`, protegido por la dependencia de autenticación existente
- [ ] T011 [P] Crear helper de almacenamiento de exportaciones (escritura/lectura/borrado con nombre UUID bajo `REPORTS_STORAGE_DIR`) en `backend/src/repse/reports/service.py`

**Checkpoint**: Modelo, esquemas, router, config y motor de filas listos — pueden empezar las historias.

---

## Phase 3: User Story 1 - Exportar reporte de un proveedor (Priority: P1) 🎯 MVP

**Goal**: Desde el detalle de un proveedor, exportar su reporte de cumplimiento en CSV o PDF (síncrono), una fila por documento esperado.

**Independent Test**: Generar el CSV de un proveedor con 5 documentos en estados mixtos y verificar 5 filas con valores que coinciden con la pantalla; generar el PDF y verificar encabezado de tenant y zona horaria.

### Tests for User Story 1 ⚠️ (escribir primero, deben fallar)

- [ ] T012 [P] [US1] Test de contrato de `POST /api/reports/exports` (sync, 201, `download_url`) en `backend/tests/contract/test_reports_contract.py`
- [ ] T013 [P] [US1] Test de integración: CSV de un proveedor con estados mixtos incluye "Faltante" y coincide con los datos del módulo `compliance` (SC-001) en `backend/tests/integration/test_reports_export.py`
- [ ] T014 [P] [US1] Test unitario de los renderers CSV y PDF, incluida la zona horaria del tenant (FR-012), en `backend/tests/unit/test_reports_renderers.py`

### Implementation for User Story 1

- [ ] T015 [P] [US1] Implementar `csv_renderer.py` en `backend/src/repse/reports/renderers/` (stdlib `csv`, UTF-8 BOM, columnas de FR-003)
- [ ] T016 [P] [US1] Crear la plantilla Jinja2 `backend/src/repse/reports/templates/report.html` (encabezado de tenant + logo, zona horaria, tabla, leyenda de estados, numeración) según FR-004
- [ ] T017 [US1] Implementar `pdf_renderer.py` en `backend/src/repse/reports/renderers/` (Jinja2 + WeasyPrint) usando `report.html` (depende de T016)
- [ ] T018 [US1] Implementar en `service.py` el flujo síncrono de `scope=single`: validar `supplier_id` del tenant, generar filas, renderizar CSV/PDF, persistir `ExportRequest` en estado `ready`, guardar archivo y registrar bitácora (FR-008) (depende de T009, T011, T015, T017)
- [ ] T019 [US1] Implementar `POST /api/reports/exports` y `GET /api/reports/exports/{id}/download` en `backend/src/repse/reports/routes.py` con verificación de sesión y tenant (FR-007); manejar proveedor inactivo en el encabezado (depende de T018)
- [ ] T020 [US1] Implementar en `frontend/src/components/reports/ExportDialog.tsx` el diálogo de formato (CSV/PDF) e integrarlo en la página de detalle de proveedor, usando `lib/api/reports.ts` para crear la exportación y disparar la descarga

**Checkpoint**: US1 funcional y testeable de forma independiente (MVP).

---

## Phase 4: User Story 2 - Reporte agregado de múltiples proveedores (Priority: P2)

**Goal**: Exportar el conjunto de proveedores resultante de los filtros del listado (o todos), con generación asíncrona por encima del umbral y notificación in-app por polling.

**Independent Test**: Filtrar 10 proveedores "Vencido"/"Por vencer" y exportar; verificar una fila por (proveedor × documento) respetando los filtros. Forzar > 50 proveedores y verificar respuesta `202` + transición a `ready` con descarga válida ≥ 24 h.

### Tests for User Story 2 ⚠️ (escribir primero, deben fallar)

- [ ] T021 [P] [US2] Test de contrato: `POST /exports` con `scope=filtered/all` devuelve `202 pending` al exceder el umbral; `GET /exports/{id}` refleja estados en `backend/tests/contract/test_reports_contract.py`
- [ ] T022 [P] [US2] Test de integración: export filtrado contiene solo los proveedores del filtro y respeta los filtros aplicados, en `backend/tests/integration/test_reports_export.py`
- [ ] T023 [P] [US2] Test de integración del flujo asíncrono: umbral → `pending` → worker → `ready`; enlace válido ≥ TTL, en `backend/tests/integration/test_reports_async.py`
- [ ] T024 [P] [US2] Test de integración de aislamiento multi-tenant: tenant A no puede leer/descargar export de tenant B → `404`; sin sesión → `401`; expirado → `410` (SC-004, SC-006), en `backend/tests/integration/test_reports_tenant_isolation.py`

### Implementation for User Story 2

- [ ] T025 [US2] Extender `service.py` para resolver `scope=filtered` y `scope=all` aplicando los mismos filtros del listado, y decidir sync/async según los umbrales configurados (FR-002, FR-006)
- [ ] T026 [US2] Implementar el worker en proceso `backend/src/repse/reports/worker.py`: tarea asyncio iniciada con la app que consume `ExportRequest` en `pending` (FIFO), genera el archivo, actualiza estado a `ready`/`failed` y registra bitácora (depende de T025)
- [ ] T027 [US2] Arrancar el worker en el ciclo de vida de la app en `backend/src/repse/main.py` (startup/lifespan)
- [ ] T028 [US2] Implementar `GET /api/reports/exports/{id}` en `routes.py` (estado + `download_url`), con verificación de tenant y códigos `404/410/409` del contrato
- [ ] T029 [US2] Implementar en `frontend/src/lib/api/reports.ts` y `ExportDialog.tsx` el polling de estado con TanStack Query (intervalo mientras `generating`) y la notificación in-app (toast/badge) al pasar a `ready`; integrar el disparo desde el listado filtrado de proveedores

**Checkpoint**: US1 y US2 funcionan de forma independiente; aislamiento multi-tenant verificado.

---

## Phase 5: User Story 3 - Empaquetar reporte con archivos originales (Priority: P3)

**Goal**: Opción de descargar un ZIP con el resumen (CSV/PDF) más los archivos originales, organizados por proveedor.

**Independent Test**: Generar el ZIP de un proveedor con 5 documentos y verificar: resumen en la raíz, una carpeta por proveedor, archivos `{tipo}_{periodo}_{fecha-carga}.{ext}`; tipo "Faltante" sin archivo y sin error.

### Tests for User Story 3 ⚠️ (escribir primero, deben fallar)

- [ ] T030 [P] [US3] Test unitario del empaquetador ZIP: estructura, nomenclatura de archivos y manejo de "Faltante", en `backend/tests/unit/test_reports_renderers.py`
- [ ] T031 [P] [US3] Test de integración: export con `include_originals=true` produce ZIP con resumen + originales; exceder `REPORTS_ZIP_MAX_BYTES` → `failed` con mensaje, en `backend/tests/integration/test_reports_export.py`

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implementar `zip_packager.py` en `backend/src/repse/reports/renderers/` (stdlib `zipfile`, estructura de FR-009, límite `REPORTS_ZIP_MAX_BYTES`)
- [ ] T033 [US3] Integrar `include_originals` en `service.py`/`worker.py`: empaquetar resumen + originales, marcar `failed` si excede el límite (depende de T032)
- [ ] T034 [US3] Añadir la opción "incluir archivos originales (ZIP)" en `frontend/src/components/reports/ExportDialog.tsx`

**Checkpoint**: Las tres historias funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cierre transversal.

- [ ] T035 [P] Implementar la limpieza periódica de exportaciones expiradas en `worker.py`: marcar `expired` y borrar archivos al vencer `expires_at`
- [ ] T036 [P] Test de integración de la limpieza/expiración (estado `expired` + archivo borrado + descarga `410`) en `backend/tests/integration/test_reports_async.py`
- [ ] T037 Verificar la auditoría completa (usuario, fecha, alcance, filtros, formato, resultado, tamaño) en todos los caminos (SC-005) y cubrirla con aserciones en los tests existentes
- [ ] T038 Ejecutar la validación de `quickstart.md` (flujo manual de los 6 escenarios) y ajustar lo necesario

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; **bloquea** todas las historias.
- **US1 (Phase 3)**: depende de Foundational. MVP.
- **US2 (Phase 4)**: depende de Foundational; reutiliza el motor de filas y el almacenamiento de US1 pero es testeable de forma independiente.
- **US3 (Phase 5)**: depende de Foundational; añade el empaquetado ZIP sobre el resumen.
- **Polish (Phase 6)**: depende de las historias deseadas completas.

### User Story Dependencies

- **US1 (P1)**: independiente tras Foundational.
- **US2 (P2)**: independiente tras Foundational (async + agregado). No requiere US3.
- **US3 (P3)**: independiente tras Foundational (empaquetado). Reutiliza el renderer de resumen.

### Within Each User Story

- Los tests se escriben y deben fallar antes de implementar.
- Modelos antes que servicios; servicios antes que endpoints; backend antes que frontend.

### Parallel Opportunities

- T003, T004 (Setup) en paralelo.
- T007, T008, T009, T011 (Foundational) en paralelo tras T005/T006.
- Tests de cada historia ([P]) en paralelo entre sí.
- Renderers CSV (T015) y plantilla PDF (T016) en paralelo.
- Tras Foundational, US1/US2/US3 pueden repartirse entre desarrolladores.

---

## Parallel Example: User Story 1

```bash
# Tests de US1 juntos (deben fallar primero):
Task: "Contract test POST /api/reports/exports en backend/tests/contract/test_reports_contract.py"
Task: "Integración CSV de un proveedor en backend/tests/integration/test_reports_export.py"
Task: "Unit renderers CSV/PDF + zona horaria en backend/tests/unit/test_reports_renderers.py"

# Implementación en paralelo:
Task: "csv_renderer.py en backend/src/repse/reports/renderers/"
Task: "Plantilla report.html en backend/src/repse/reports/templates/"
```

---

## Implementation Strategy

### MVP First (solo US1)

1. Phase 1: Setup
2. Phase 2: Foundational (CRÍTICO — bloquea todo)
3. Phase 3: US1 → exportar CSV/PDF de un proveedor
4. **PARAR y VALIDAR**: probar US1 de forma independiente
5. Desplegar/demo si está listo

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1 → CSV/PDF por proveedor (MVP)
3. US2 → agregado + async + polling + aislamiento verificado
4. US3 → ZIP con originales
5. Polish → limpieza/expiración + auditoría + quickstart

---

## Notes

- [P] = archivos distintos, sin dependencias.
- Verificar que los tests fallan antes de implementar (Constitución III).
- Aislamiento multi-tenant (T024) y autorización de descarga son críticos: no mergear sin ellos en verde.
- Commit tras cada tarea o grupo lógico.
