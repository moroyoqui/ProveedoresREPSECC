# Tasks: Vista de Cumplimiento Anual del Proveedor

**Input**: Design documents from `specs/006-supplier-compliance-view/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/compliance.md](./contracts/compliance.md)

**Tests**: Se incluyen tests para `cell_status` (path crítico, obligatorio por Principio III de la constitución) y el endpoint (aislamiento multi-tenant obligatorio).

**Organization**: Tareas agrupadas por historia de usuario; US1 y US2 se fusionan en una sola fase (P1) porque la cuadrícula y el código de colores son inseparables.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: Historia de usuario a la que pertenece la tarea

---

## Phase 1: Setup

**Purpose**: Crear la estructura del módulo `compliance/` en el backend.

- [ ] T001 Crear `backend/src/repse/compliance/__init__.py` (archivo vacío — registra el módulo Python)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schemas y tipos compartidos que bloquean todas las historias de usuario.

**⚠️ CRITICAL**: Ninguna historia puede empezar hasta completar esta fase.

- [ ] T002 Definir schemas Pydantic en `backend/src/repse/compliance/schemas.py`: enum `CellStatus` con literales `validated | submitted | expired | missing | pending | future | not_required`; dataclasses `CellOut`, `MonthlyRequirementOut`, `OneTimeRequirementOut`, `SupplierSummaryOut`, `ComplianceGridOut`; shapes exactos según [contracts/compliance.md](./contracts/compliance.md)
- [ ] T003 [P] Agregar función `suppliersApi.compliance(supplierId: number, year: number)` a `frontend/src/lib/api/index.ts` con el tipo de respuesta TypeScript correspondiente a `ComplianceGridOut`

**Checkpoint**: Schemas listos — las fases de historias de usuario pueden comenzar.

---

## Phase 3: US1 + US2 — Cuadrícula anual con código de colores (Priority: P1) 🎯 MVP

**Goal**: Al hacer clic en un proveedor, se muestra la cuadrícula de 12 meses con esferas de color indicando el estado de cumplimiento de cada tipo de documento por mes.

**Independent Test**: Navegar a `/suppliers/:id` con un proveedor que tenga documentos en distintos estados; verificar que la cuadrícula muestra 12 columnas de meses, una fila por tipo de documento, y que las esferas tienen los colores correctos (verde/amarillo/rojo/gris). Probar con `curl GET /api/v1/suppliers/{id}/compliance?year=2026` directamente.

### Tests para US1 + US2 (obligatorios por constitución — Principio III)

- [ ] T004 [US1] Escribir unit tests en `backend/tests/unit/test_compliance_service.py` cubriendo los 7 estados de `cell_status`: `validated` (doc verified), `submitted` (doc not verified), `expired` (doc status=expired), `missing` (mes pasado sin doc), `pending` (mes actual sin doc), `future` (mes futuro sin doc), `not_required` (mes no aplica para la periodicidad). Los tests deben **fallar** antes de que exista la implementación.
- [ ] T005 [US1] Escribir integration test en `backend/tests/integration/test_compliance_routes.py`: caso happy path (GET compliance devuelve 200 con estructura correcta) y caso negativo multi-tenant (usuario de Org A solicita compliance de proveedor de Org B → 404). Tests deben **fallar** antes de la implementación.

### Implementación para US1 + US2

- [ ] T006 [US1] Implementar `backend/src/repse/compliance/service.py` con: función `effective_periodicity(req, doc_type)` que resuelve `periodicity_override` o hereda del `DocumentType`; función `applicable_months(periodicity)` → lista de ints (ver [research.md §3](./research.md)); función `cell_status(doc, month, year, today)` → `CellStatus` con las 7 reglas del [data-model.md](./data-model.md); función asíncrona `get_annual_compliance(db, supplier_id, year, org_id)` → `ComplianceGridOut` usando las dos queries del data-model (requisitos activos + documentos del año).
- [ ] T007 [P] [US1] Implementar `backend/src/repse/compliance/routes.py`: `GET /api/v1/suppliers/{supplier_id}/compliance` con query param `year` (default año actual, rango 2020–año actual); inyectar `current_user` y `current_tenant` como en el resto de rutas del proyecto; devolver 404 si el proveedor no pertenece al tenant.
- [ ] T008 [US1] Registrar el compliance router en `backend/src/repse/main.py` bajo el prefijo `/api/v1`.
- [ ] T009 [P] [US1] Crear componente `frontend/src/components/suppliers/ComplianceCell.tsx`: esfera SVG o `div` redondeado con el color correspondiente al `CellStatus`; Radix Tooltip con descripción textual del estado; celda vacía (sin esfera) para `not_required`.

  Paleta de colores Tailwind:
  - `validated` → `bg-green-500`
  - `submitted` → `bg-yellow-400`
  - `expired` → `bg-red-700`
  - `missing` → `bg-red-500`
  - `pending` → `bg-gray-300`
  - `future` → `bg-gray-200`
  - `not_required` → sin esfera, celda vacía

- [ ] T010 [US1] Crear componente `frontend/src/components/suppliers/ComplianceGrid.tsx`: CSS Grid con `grid-cols-[minmax(160px,1fr)_repeat(12,minmax(0,40px))]`; fila de encabezado con abreviaturas de mes (Ene–Dic) pegada al top (`sticky top-0 bg-white z-10`); mes actual con columna resaltada (fondo sutil `bg-brand-50`); una fila por cada item de `monthly_requirements`; cada celda renderiza `ComplianceCell`; una leyenda debajo del grid con los cuatro estados visibles (validated/submitted/missing/future).
- [ ] T011 [US1] Modificar `frontend/src/pages/suppliers/detail.tsx`: agregar query `useQuery(['supplier-compliance', supplierId, year], () => suppliersApi.compliance(supplierId, year))`; reemplazar la sección "Documentos requeridos" (tabla plana) por el componente `ComplianceGrid`; mostrar spinner mientras carga; estado vacío si `monthly_requirements` está vacío.

**Checkpoint**: Las US1 y US2 son completamente funcionales. La cuadrícula con colores es visible al entrar al detalle de un proveedor.

---

## Phase 4: US3 — Documentos sin periodicidad (Priority: P2)

**Goal**: Debajo de la cuadrícula mensual se muestra una sección con los documentos que tienen `periodicity = "none"`, con su estado actual.

**Independent Test**: Asignar al tipo de proveedor un requisito con `DocumentType.periodicity='none'`; entrar al detalle del proveedor y verificar que aparece la sección "Documentos sin periodicidad" con el estado correcto.

### Implementación para US3

- [ ] T012 [P] [US3] Crear componente `frontend/src/components/suppliers/OneTimeRequirements.tsx`: lista de tarjetas compactas, una por item de `one_time_requirements`; cada tarjeta muestra nombre del tipo, esfera de color (mismo `ComplianceCell` reutilizado), fecha de vencimiento si `due_date_effective` no es null, botón "Ver" si `document_id` no es null.
- [ ] T013 [US3] Actualizar `frontend/src/pages/suppliers/detail.tsx`: renderizar `<OneTimeRequirements items={data.one_time_requirements} supplierId={supplierId} />` debajo del `ComplianceGrid`; solo mostrar la sección si `one_time_requirements.length > 0`.

**Checkpoint**: La pantalla de detalle muestra la cuadrícula mensual Y la sección de documentos de entrega única.

---

## Phase 5: US4 — Navegación desde celda (Priority: P3)

**Goal**: Hacer clic en una esfera verde/amarilla/roja abre el documento correspondiente; hacer clic en una esfera roja/gris (missing/pending) abre el diálogo de carga preconfigurado.

**Independent Test**: Hacer clic en una celda verde → verificar que se abre el detalle del documento (o redirige a la URL del documento). Hacer clic en una celda roja (missing) → verificar que se abre `UploadDialog` con `document_type_id` y `coverage_period_start` precargados.

### Implementación para US4

- [ ] T014 [US4] Actualizar `frontend/src/components/suppliers/ComplianceCell.tsx`: cuando `status` es `validated`, `submitted` o `expired` y `document_id != null`, envolver la esfera en un botón que dispara `onDocumentClick(document_id)` (prop callback).
- [ ] T015 [US4] Actualizar `frontend/src/components/suppliers/ComplianceCell.tsx`: cuando `status` es `missing` o `pending`, envolver la esfera en un botón que dispara `onUploadClick({ document_type_id, coverage_period_start })` (prop callback).
- [ ] T016 [US4] Actualizar `frontend/src/pages/suppliers/detail.tsx`: implementar `onDocumentClick` como navegación a `GET /api/v1/documents/{id}/download-token` (emitir token y abrir archivo, igual que el flujo ya existente); implementar `onUploadClick` como apertura de `UploadDialog` con los campos precargados.
- [ ] T017 [P] [US4] Actualizar `frontend/src/components/suppliers/OneTimeRequirements.tsx`: el botón "Ver" de una tarjeta dispara el mismo `onDocumentClick`; si `document_id` es null, mostrar botón "Subir" que dispara `onUploadClick({ document_type_id, coverage_period_start: null })`.

**Checkpoint**: La cuadrícula completa es accionable — clic en cualquier esfera ejecuta la acción contextual correcta.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Accesibilidad, estado vacío y validación final.

- [ ] T018 [P] Agregar `aria-label` descriptivo a cada esfera en `ComplianceCell.tsx` (p. ej. `"Enero: validado"`, `"Marzo: faltante"`) para accesibilidad de lectores de pantalla.
- [ ] T019 [P] Agregar estado vacío en `SupplierDetailPage` cuando `monthly_requirements` y `one_time_requirements` están ambos vacíos: mostrar mensaje "Este proveedor no tiene requisitos de documentación configurados. Configura el tipo de proveedor en Catálogos."
- [ ] T020 Ejecutar validación del [quickstart.md](./quickstart.md): correr `pytest backend/tests/unit/test_compliance_service.py backend/tests/integration/test_compliance_routes.py -v` y confirmar que todos los tests pasan.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — iniciar inmediatamente.
- **Foundational (Phase 2)**: Depende de Phase 1 — **bloquea todas las historias**.
- **US1+US2 (Phase 3)**: Depende de Phase 2. Incluye tests obligatorios antes de la implementación.
- **US3 (Phase 4)**: Puede iniciar en paralelo con Phase 3 en frontend una vez que T002/T003 están listos; el componente `OneTimeRequirements` es independiente del grid.
- **US4 (Phase 5)**: Depende de Phase 3 (necesita `ComplianceCell`) y del `UploadDialog` existente.
- **Polish (Phase 6)**: Depende de todas las historias completadas.

### User Story Dependencies

- **US1+US2 (P1)**: Iniciar después de Phase 2. Sin dependencias entre historias.
- **US3 (P2)**: El componente `OneTimeRequirements` puede construirse en paralelo con la cuadrícula (T012 en paralelo con T009/T010); T013 depende de T011.
- **US4 (P3)**: Depende de T009 (`ComplianceCell` creado) y del `UploadDialog` existente.

### Within Each Phase

- Tests (T004, T005) **deben escribirse y fallar** antes de T006/T007.
- T006 (service) → T007 (routes) → T008 (register router).
- T009 (ComplianceCell) → T010 (ComplianceGrid) → T011 (detail page).
- T012 (OneTimeRequirements) puede ejecutarse en paralelo con T009.

### Parallel Opportunities

- T003 (frontend types) en paralelo con T002 (backend schemas) — archivos distintos.
- T004 (unit tests) en paralelo con T005 (integration tests) — archivos distintos.
- T007 (routes) en paralelo con T009 (ComplianceCell) — backend vs frontend.
- T012 (OneTimeRequirements) en paralelo con T009/T010 (grid components).
- T018 y T019 en paralelo (último phase).

---

## Parallel Example: Phase 3 (US1+US2)

```
# Una vez completada la Phase 2, se pueden lanzar en paralelo:

Backend:
  Task T004: unit tests cell_status (backend/tests/unit/test_compliance_service.py)
  Task T005: integration tests endpoint (backend/tests/integration/test_compliance_routes.py)

Frontend:
  Task T003: suppliersApi.compliance() (frontend/src/lib/api/index.ts)

# Luego, con T004/T005 fallando (TDD):
  Task T006: service.py — cell_status + get_annual_compliance
  Task T007: routes.py (paralelo con T009 en frontend)
  Task T009: ComplianceCell.tsx (paralelo con T007 en backend)

# Luego:
  Task T008: registrar router en main.py
  Task T010: ComplianceGrid.tsx (depende de T009)
  Task T011: detail.tsx (depende de T010 + T008)
```

---

## Implementation Strategy

### MVP First (US1 + US2 solamente)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (schemas + tipos TS)
3. Completar Phase 3: US1+US2 (cuadrícula con colores)
4. **STOP y VALIDAR**: probar la cuadrícula en el navegador con un proveedor real
5. Demo / deploy si está listo

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1+US2 → cuadrícula mensual funcional con colores → Demo MVP
3. US3 → sección de documentos sin periodicidad → Demo
4. US4 → celdas accionables (clic para ver/subir) → Demo completo
5. Polish → accesibilidad y estados vacíos → Release

---

## Notes

- `[P]` = archivos distintos, sin dependencias pendientes — se pueden ejecutar en paralelo
- `[USn]` = traza la tarea a la historia de usuario
- Los tests T004 y T005 son **obligatorios** por la constitución del proyecto (Principio III — paths críticos)
- `cell_status` en `service.py` es el algoritmo central; los unit tests la documentan y protegen de regresiones
- El `UploadDialog` existente en `frontend/src/components/documents/UploadDialog.tsx` se reutiliza en US4 — no hay que crearlo
- El token de descarga de documentos ya existe (`POST /api/v1/documents/{id}/download-token`) — reutilizar en US4
