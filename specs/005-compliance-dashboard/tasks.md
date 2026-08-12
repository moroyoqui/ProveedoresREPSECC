---
description: "Task list for 005 — Tablero de Control de Cumplimiento"
---

# Tasks: Tablero de Control de Cumplimiento

**Input**: Design documents from `/specs/005-compliance-dashboard/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/dashboard-api.md ✓, quickstart.md ✓

**Tests**: INCLUIDOS — la constitución III (Test-First en rutas críticas) y el quickstart exigen tests de agregación (SC-007), consistencia (SC-003), aislamiento (SC-006) y contrato antes de la implementación.

**Organization**: Tareas agrupadas por user story. Backend agrega en servidor y reutiliza `documents.status.compute_status` y la lógica de requisitos por `SupplierType` del módulo `compliance`. Sin migraciones de base de datos (solo lectura).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: User story a la que pertenece (US1–US4)
- Rutas exactas incluidas en cada descripción

## Path Conventions (web app, según plan.md)

- Backend: `backend/src/repse/`, tests en `backend/tests/{contract,integration,unit}/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Crear el esqueleto del módulo backend y la dependencia de gráficos del frontend.

- [X] T001 Crear el paquete del módulo backend `backend/src/repse/dashboard/` con `__init__.py`, `schemas.py`, `service.py` y `routes.py` vacíos (firmas/stubs), siguiendo el patrón `schemas/service/routes` de los módulos existentes (sin `models.py`, no hay entidades nuevas).
- [X] T002 [P] Añadir la dependencia `recharts` al frontend: `cd frontend && npm i recharts --legacy-peer-deps` y verificar que queda registrada en `frontend/package.json`.
- [X] T003 [P] Crear `frontend/src/lib/api/dashboard.ts` con el stub del cliente y los tipos TypeScript que reflejan el contrato (`DashboardOut`, `PieSlice`, `DocTypeBar`, `Kpis`, `SupplierRow`, `DashboardFilters`) de `contracts/dashboard-api.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura común que TODAS las user stories necesitan: schemas Pydantic, cache versionado por tenant y el endpoint base registrado bajo `_BACKOFFICE`.

**⚠️ CRITICAL**: Ninguna user story puede completarse hasta terminar esta fase.

- [X] T004 [P] Definir los schemas Pydantic v2 en `backend/src/repse/dashboard/schemas.py`: `DashboardFilters` (year, supplier_type_ids, document_type_ids, supplier_ids, statuses, include_inactive), `PieSlice`, `DocTypeBar`, `Kpis`, `SupplierRow` y `DashboardOut` (con `filters`, `pie`, `by_document_type`, `kpis`, `suppliers`, `available_years`, `calculated_at`, `empty_reason`) según `data-model.md` y `contracts/dashboard-api.md`.
- [X] T005 [P] Implementar `TenantVersionedTTLCache` en `backend/src/repse/common/cache.py`: dict en memoria con TTL de 60 s, clave `(organization_id, tenant_version, filtros_normalizados)`, contador de versión por tenant `dict[int,int]` y función `bump_tenant_version(organization_id)` (research §4, data-model `CacheEntry`).
- [X] T006 Implementar la normalización de filtros en `backend/src/repse/dashboard/service.py`: orden estable + dedupe de las listas de IDs/estados para producir la porción de la clave de cache; validación de `year ∈ [2020, año_actual]` → `400 invalid_year` y `status` desconocido → `400 invalid_status` (data-model §Reglas de validación). IDs fuera del tenant se ignoran silenciosamente.
- [X] T007 Implementar la resolución de la fecha de referencia (`ref_date`) en `backend/src/repse/dashboard/service.py` en zona horaria del tenant (default `America/Mexico_City`): año en curso → hoy (FR-011); año pasado → 31-dic 23:59 (FR-012); año futuro → conjunto vacío (research §3/§5).
- [X] T008 Crear la ruta base `GET /api/v1/dashboard/compliance` en `backend/src/repse/dashboard/routes.py` que parsea los query params (repetibles) a `DashboardFilters`, llama al servicio y devuelve `DashboardOut`; registrar `dashboard_router` en `backend/src/repse/main.py` con `prefix=f"{API_PREFIX}/dashboard"`, `tags=["dashboard"]` y `dependencies=_BACKOFFICE` (quickstart Backend §5).

**Checkpoint**: Endpoint accesible y aislado por tenant; schemas y cache listos — las user stories pueden empezar.

---

## Phase 3: User Story 1 - Vista global del cumplimiento del año en curso (Priority: P1) 🎯 MVP

**Goal**: Al abrir el tablero (sin filtros), el usuario ve pastel por estado, barras por tipo de documento, KPIs y tabla resumen del año en curso, con el pastel sumando exactamente 100%.

**Independent Test**: Cargar el tablero como usuario de un tenant con ≥10 proveedores con documentos en distintos estados y verificar que pastel + barras + KPIs + tabla cargan sin filtros y reflejan el año en curso.

### Tests for User Story 1 ⚠️ (escribir primero, deben FALLAR antes de implementar)

- [X] T009 [P] [US1] Test unitario de agregación en `backend/tests/unit/test_dashboard_aggregation.py`: suma del pastel == 100% con redondeo Hamilton (SC-007), derivación de `missing` desde requisitos activos, y cálculo de KPIs (`global_compliance_percent`, `active_suppliers`, `at_risk_suppliers`, `expiring_30d`).
- [X] T010 [P] [US1] Test de contrato en `backend/tests/contract/test_dashboard_contract.py`: forma de la respuesta 200 del contrato, `sum(pie[*].percent)==100`, y 403 para rol supplier / 401 sin sesión.
- [X] T011 [P] [US1] Test de integración de consistencia y aislamiento en `backend/tests/integration/test_dashboard_consistency.py`: cero discrepancias tablero↔`GET /suppliers/{id}/compliance` (SC-003) y tenant A no ve agregados de tenant B (SC-006).

### Implementation for User Story 1

- [X] T012 [US1] Implementar la derivación de "celdas requeridas" en `backend/src/repse/dashboard/service.py`: expandir `SupplierTypeDocumentRequirement` activos × `DocumentType` activos por periodicidad sobre el año, reutilizando helpers de `compliance.service` (`applicable_months`, `effective_periodicity`); excluir tipos inactivos del cálculo de `missing` (FR-014).
- [X] T013 [US1] Implementar la agregación en servidor en `backend/src/repse/dashboard/service.py`: consultas `GROUP BY` scoped por `organization_id`, estado de cada documento vía `documents.status.compute_status(doc, today=ref_date, ...)`; producir `pie` (con redondeo Hamilton, research §7), `by_document_type` (conteos por estado + `compliance_percent`), `kpis` y `suppliers` (tabla resumen). Definir `at_risk_suppliers` exactamente como FR-004a.
- [X] T014 [US1] Calcular `available_years` (años con ≥1 documento del tenant + año en curso, máx. 10 hacia atrás) y `calculated_at` (hora local del tenant) en `backend/src/repse/dashboard/service.py`; manejar `empty_reason="no_suppliers"` cuando el tenant no tiene proveedores (FR-019).
- [X] T015 [US1] Integrar el cache en `backend/src/repse/dashboard/service.py`: leer/escribir `TenantVersionedTTLCache` con la clave normalizada antes de recalcular (FR-021).
- [X] T016 [P] [US1] Implementar el hook `useDashboard(filters)` con TanStack Query v5 en `frontend/src/lib/api/dashboard.ts` (query key = filtros normalizados).
- [X] T017 [P] [US1] Implementar `StatusPieChart.tsx` en `frontend/src/components/dashboard/` con Recharts (`Cell` coloreado por estado, tooltip/leyenda accesibles).
- [X] T018 [P] [US1] Implementar `DocTypeBarChart.tsx` en `frontend/src/components/dashboard/` (barras de cumplimiento por tipo de documento).
- [X] T019 [P] [US1] Implementar `KpiStrip.tsx` en `frontend/src/components/dashboard/` (cumplimiento global %, proveedores activos, proveedores en riesgo, por vencer 30 días).
- [X] T020 [P] [US1] Implementar `ComplianceSummaryTable.tsx` en `frontend/src/components/dashboard/` (fila por proveedor con `compliance_percent`, `expired`, `missing`).
- [X] T021 [US1] Reemplazar el placeholder en `frontend/src/pages/dashboard/index.tsx`: orquestar `useDashboard`, montar los 4 componentes, mostrar el indicador de `calculated_at` (zona del tenant, FR-021b) y el estado vacío `no_suppliers` (FR-019).
- [X] T022 [P] [US1] Test frontend en `frontend/tests/`: render de la vista por defecto con datos sembrados (pastel + barras + KPIs + tabla) y estado vacío `no_suppliers`.

**Checkpoint**: US1 totalmente funcional y testeable de forma independiente — MVP entregable.

---

## Phase 4: User Story 2 - Filtrar por año (Priority: P1)

**Goal**: El selector de año (años con datos, default últimos 5/máx. 10) recalcula todo el tablero; años pasados se evalúan al cierre 31-dic (estado fotográfico).

**Independent Test**: Cambiar el año al anterior y verificar que pastel, barras y KPIs reflejan documentos cuyo periodo cubierto cae en ese año, evaluados al cierre de ese año.

### Tests for User Story 2 ⚠️

- [X] T023 [P] [US2] Test unitario en `backend/tests/unit/test_dashboard_aggregation.py`: año pasado usa `ref_date=31-dic 23:59` del año (FR-012); año en curso usa hoy (FR-011); alcance por periodo cubierto que intersecta el año, documentos "sin vigencia" solo si la fecha de carga cae en el año (FR-013).
- [X] T024 [P] [US2] Test de contrato en `backend/tests/contract/test_dashboard_contract.py`: `year` fuera de `[2020, año_actual]` → `400 invalid_year`; año futuro → 200 con `empty_reason="no_data_for_filters"`; `available_years` correcto.

### Implementation for User Story 2

- [X] T025 [US2] Extender el servicio en `backend/src/repse/dashboard/service.py` para aplicar el filtro `year` al alcance de documentos (intersección de periodo cubierto + regla de "sin vigencia", FR-013) usando la `ref_date` ya resuelta en T007.
- [X] T026 [US2] Manejar `empty_reason="no_data_for_filters"` cuando el año seleccionado no tiene datos en `backend/src/repse/dashboard/service.py` (FR-018).
- [X] T027 [US2] Añadir el selector de año (alimentado por `available_years`) en `frontend/src/pages/dashboard/index.tsx`, sincronizado con `useSearchParams` (param `year`).
- [X] T028 [P] [US2] Test frontend en `frontend/tests/`: cambiar el año dispara refetch con el nuevo param y el estado vacío por año sin datos se renderiza (no gráfico vacío).

**Checkpoint**: US1 + US2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Filtrar por tipo de documento y otros cortes (Priority: P2)

**Goal**: Filtros multi-selección por tipo de proveedor, tipo de documento, proveedor y estado, codificados en la URL, con "Limpiar filtros"; el pastel mantiene 100% sobre el subconjunto.

**Independent Test**: Filtrar por tipo "Opinión SAT" + estado "Vencido" y verificar que los componentes muestran solo ese subconjunto, con el pastel sumando 100% relativo.

### Tests for User Story 3 ⚠️

- [X] T029 [P] [US3] Test unitario en `backend/tests/unit/test_dashboard_aggregation.py`: con filtros aplicados (tipo/estado/proveedor/tipo de proveedor) el pastel suma 100% del subconjunto (SC-007) y los conteos entre componentes son consistentes (FR-007).
- [X] T030 [P] [US3] Test de contrato en `backend/tests/contract/test_dashboard_contract.py`: params repetibles (`supplier_type`, `document_type`, `supplier`, `status`, `include_inactive`); `status` inválido → `400 invalid_status`; IDs fuera del tenant se ignoran sin error.

### Implementation for User Story 3

- [X] T031 [US3] Aplicar todos los filtros (supplier_type incl. "Sin clasificar"=0, document_type, supplier, status, include_inactive) en las consultas agregadas de `backend/src/repse/dashboard/service.py`, manteniendo el redondeo Hamilton sobre el subconjunto filtrado (FR-006/FR-007).
- [X] T032 [US3] Implementar los controles de filtro (multi-selección de tipo de proveedor, tipo de documento, proveedor con búsqueda nombre/RFC, estado, toggle inactivos) y el botón "Limpiar filtros" en `frontend/src/pages/dashboard/index.tsx`, codificados en `useSearchParams` (FR-008/FR-009).
- [X] T033 [P] [US3] Test frontend en `frontend/tests/`: aplicar filtros actualiza la URL; recargar reconstruye los filtros (FR-008); "Limpiar filtros" vuelve al default (FR-009).

**Checkpoint**: US1 + US2 + US3 funcionan de forma independiente.

---

## Phase 6: User Story 4 - Drill-down desde el tablero al listado (Priority: P2)

**Goal**: Click en porción del pastel, barra o KPI navega al listado existente con los filtros del tablero + la dimensión seleccionada ya aplicados (sin endpoint nuevo).

**Independent Test**: Click en la porción "Vencido" del pastel abre el listado de documentos en estado "Vencido" con el mismo año/tipo del tablero.

### Implementation for User Story 4

- [X] T034 [US4] Añadir handler `onClick` a `StatusPieChart.tsx` (`frontend/src/components/dashboard/`) que navega al listado de documentos con `status=<estado>` + filtros activos (FR-015).
- [X] T035 [US4] Añadir handler `onClick` a `DocTypeBarChart.tsx` (`frontend/src/components/dashboard/`) que navega al listado con `document_type=<id>` + filtros activos (FR-016).
- [X] T036 [US4] Añadir navegación desde `KpiStrip.tsx` (`frontend/src/components/dashboard/`): "proveedores en riesgo" → listado con `status=expired,missing`; "por vencer 30 días" → documentos `status=expiring_soon` acotado a 30 días (FR-017).
- [X] T037 [P] [US4] Test frontend en `frontend/tests/`: cada interacción de drill-down navega a la URL del listado con los filtros del tablero propagados correctamente (SC-005).

**Checkpoint**: Las cuatro user stories funcionan de forma independiente.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Invalidación de cache, accesibilidad y validación final.

- [X] T038 Conectar `bump_tenant_version(organization_id)` en los puntos de mutación (FR-021a): servicios de `documents` (alta/edición/borrado), catálogo `document_types` (activar/desactivar/archivar), `suppliers` (alta/baja/reactivación) y cambios de configuración que afecten el estado (umbral "por vencer", overrides de vencimiento).
- [X] T039 [P] [US3] Etiquetar los documentos sobre tipos inactivos con `inactive: true` en `by_document_type` y mostrar el indicador "tipo inactivo" en `DocTypeBarChart.tsx` / `ComplianceSummaryTable.tsx` (FR-014, edge case de tipos desactivados).
- [X] T040 [P] Accesibilidad y branding de los gráficos (colores por estado coherentes con Tailwind, leyendas/tooltips con texto legible) en `frontend/src/components/dashboard/`.
- [X] T041 Ejecutar la validación de `quickstart.md`: `pytest backend/tests/{unit,integration,contract}/test_dashboard_*.py` + `cd frontend && npm run test:run`, y recorrer el checklist manual (FR-002/003/007/008/009/012/015–019/021b, SC-003/006/007).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — empieza de inmediato.
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las user stories.
- **User Stories (Phase 3–6)**: dependen de Foundational. US1 es el MVP; US2/US3/US4 amplían sobre el mismo servicio/página.
- **Polish (Phase 7)**: depende de las user stories deseadas completas.

### User Story Dependencies

- **US1 (P1)**: solo depende de Foundational. Es el MVP; crea servicio, página y los 4 componentes.
- **US2 (P1)**: depende de Foundational; usa la `ref_date` de T007 y extiende el servicio/página de US1.
- **US3 (P2)**: depende de Foundational; extiende el filtrado del servicio (T013) y los controles de la página (T021).
- **US4 (P2)**: depende de los componentes de US1 (T017–T019) para colgar los handlers de drill-down; independiente de US2/US3 a nivel de prueba.

### Within Each User Story

- Tests escritos y en FALLO antes de implementar.
- Servicio (agregación) antes que endpoint/UI.
- Componentes antes de la integración en la página.

### Parallel Opportunities

- Setup: T002 y T003 en paralelo (T001 primero crea el paquete).
- Foundational: T004 y T005 en paralelo; T006/T007 dependen de T004; T008 cierra la fase.
- Tests de cada story marcados [P] corren juntos.
- Componentes frontend de US1 (T017–T020) en paralelo entre sí y con el backend de US1.

---

## Parallel Example: User Story 1

```bash
# Lanzar los tests de US1 juntos (deben fallar primero):
Task: "Test unitario de agregación en backend/tests/unit/test_dashboard_aggregation.py"
Task: "Test de contrato en backend/tests/contract/test_dashboard_contract.py"
Task: "Test de integración en backend/tests/integration/test_dashboard_consistency.py"

# Lanzar los componentes de visualización de US1 juntos:
Task: "StatusPieChart.tsx en frontend/src/components/dashboard/"
Task: "DocTypeBarChart.tsx en frontend/src/components/dashboard/"
Task: "KpiStrip.tsx en frontend/src/components/dashboard/"
Task: "ComplianceSummaryTable.tsx en frontend/src/components/dashboard/"
```

---

## Implementation Strategy

### MVP First (solo User Story 1)

1. Completar Phase 1: Setup.
2. Completar Phase 2: Foundational (CRÍTICO — bloquea todo).
3. Completar Phase 3: User Story 1.
4. **PARAR y VALIDAR**: probar US1 de forma independiente (pastel suma 100%, consistencia con detalle, aislamiento).
5. Desplegar/demostrar si está listo.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → vista por defecto del año en curso (MVP).
3. US2 → filtro de año con snapshot histórico.
4. US3 → filtros multi-selección + URL.
5. US4 → drill-down al listado.
6. Polish → invalidación de cache, tipos inactivos, a11y, validación quickstart.
