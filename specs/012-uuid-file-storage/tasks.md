---

description: "Task list: UUID Suffix en Nombres de Archivo de Documentos"

---

# Tasks: UUID Suffix en Nombres de Archivo de Documentos (012)

**Input**: Design documents from `/specs/012-uuid-file-storage/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅

**Tests**: Incluidos — el plan.md los especifica explícitamente.

**Organization**: Tareas agrupadas por user story para permitir implementación y prueba independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias incompletas)
- **[Story]**: User story a la que pertenece la tarea (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Sin nueva infraestructura requerida. Solo creación del archivo de tests vacío.

- [x] T001 Crear archivo de tests `backend/tests/unit/test_file_storage.py` con imports y fixture `tmp_path` de pytest

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Sin bloqueantes adicionales. El módulo `uuid` es stdlib. La fase Setup (T001) es el único prerequisito.

**Checkpoint**: Con T001 completo se puede iniciar cualquier user story.

---

## Phase 3: User Story 1 — Subida genera ruta única garantizada (Priority: P1) 🎯 MVP

**Goal**: Cada archivo almacenado obtiene un UUID4 en su nombre, garantizando que dos subidas con los mismos parámetros producen rutas distintas en disco.

**Independent Test**: Subir el mismo archivo dos veces para el mismo proveedor y verificar que existen dos archivos físicamente distintos en disco.

### Tests para User Story 1

> **Escribir y confirmar que FALLAN antes de implementar.**

- [x] T002 [P] [US1] Test `test_two_saves_produce_distinct_paths`: dos llamadas a `FileStore.save()` con mismos parámetros → rutas distintas, en `backend/tests/unit/test_file_storage.py`
- [x] T003 [P] [US1] Test `test_saved_path_contains_valid_uuid4`: verificar que el segmento entre versión y extensión es un UUID4 válido (`uuid.UUID(segment, version=4)`), en `backend/tests/unit/test_file_storage.py`

### Implementación para User Story 1

- [x] T004 [US1] Añadir `import uuid` al bloque de imports de `backend/src/repse/documents/storage.py` (después de los imports existentes)
- [x] T005 [US1] Modificar línea 58 de `backend/src/repse/documents/storage.py`: cambiar `rel = f"{organization_id}/{supplier_id}/{document_id}/v{version}.{ext}"` a `rel = f"{organization_id}/{supplier_id}/{document_id}/v{version}.{uuid.uuid4()}.{ext}"` (depende de T004)

**Checkpoint**: Con T002–T005 completos, US1 es funcional e independientemente verificable.

---

## Phase 4: User Story 2 — Descarga transparente para el usuario (Priority: P2)

**Goal**: Los archivos almacenados con UUID en la ruta se descargan correctamente; el contenido descargado es íntegro.

**Independent Test**: Subir un archivo con el nuevo código y abrirlo por la ruta almacenada; el contenido leído debe ser idéntico al original.

### Tests para User Story 2

> **Escribir y confirmar que FALLAN antes de implementar.** (En este caso los tests ya pasan si US1 está correcto — confirmar que pasan.)

- [x] T006 [P] [US2] Test `test_open_returns_saved_content`: guardar un archivo y abrirlo con `FileStore.open(stored.relative_path)`; verificar integridad de contenido, en `backend/tests/unit/test_file_storage.py`

### Implementación para User Story 2

> US2 no requiere cambios de código adicionales — `FileStore.open()` ya opera sobre la ruta almacenada sin reconstruirla. Los tests confirman el comportamiento correcto.

**Checkpoint**: T006 pasa → US2 verificada.

---

## Phase 5: User Story 3 — Compatibilidad con documentos existentes (Priority: P3)

**Goal**: Archivos almacenados con el formato antiguo (sin UUID) siguen siendo accesibles; las operaciones de eliminación también funcionan correctamente con la nueva nomenclatura.

**Independent Test**: Crear manualmente un archivo con el formato antiguo (`v1.pdf`) en `tmp_path`, registrarlo con esa ruta, y verificar que `FileStore.open()` y `FileStore.delete()` lo manejan sin errores.

### Tests para User Story 3

- [x] T007 [P] [US3] Test `test_delete_removes_file`: guardar archivo con nueva nomenclatura y eliminarlo con `FileStore.delete(stored.relative_path)`; verificar que el archivo no existe en disco, en `backend/tests/unit/test_file_storage.py`
- [x] T008 [P] [US3] Test `test_legacy_path_readable`: crear archivo manualmente en `tmp_path` con ruta formato antiguo (`1/1/1/v1.pdf`) y verificar que `FileStore.open("1/1/1/v1.pdf")` lo lee correctamente, en `backend/tests/unit/test_file_storage.py`

### Implementación para User Story 3

> US3 no requiere cambios de código — la retrocompatibilidad es inherente al diseño. Los tests documentan el contrato.

**Checkpoint**: T007–T008 pasan → US3 verificada.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación final y actualización de docstring.

- [x] T009 [P] Actualizar el docstring de `FileStore` en `backend/src/repse/documents/storage.py` para reflejar el nuevo formato de ruta con UUID (línea 3-4 del módulo)
- [x] T010 Ejecutar suite completa de tests unitarios: `pytest backend/tests/unit/ -v` y confirmar que todos pasan (depende de T002–T008)
- [x] T011 Ejecutar tests de integración de documentos: `pytest backend/tests/integration/test_documents_upload.py -v` para confirmar que el cambio no rompe el flujo de upload existente (depende de T005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1 — T001)**: Sin dependencias, iniciar inmediatamente
- **User Story 1 (Phase 3 — T002–T005)**: Depende de T001; T002 y T003 (tests) ANTES que T004–T005 (impl)
- **User Story 2 (Phase 4 — T006)**: Depende de T005; en paralelo con US3
- **User Story 3 (Phase 5 — T007–T008)**: Depende de T001; en paralelo con US2
- **Polish (Phase 6 — T009–T011)**: Depende de US1, US2, US3 completas

### User Story Dependencies

- **US1 (P1)**: Bloqueante para US2; US3 solo requiere T001
- **US2 (P2)**: Depende de US1 (necesita la nueva ruta para probar descarga)
- **US3 (P3)**: Independiente de US1/US2 (prueba rutas antiguas)

### Dentro de cada User Story

- Tests escritos y confirmados en ROJO antes de implementar
- T004 (import) antes de T005 (uso)
- T002/T003 pueden ejecutarse en paralelo
- T007/T008 pueden ejecutarse en paralelo

### Parallel Opportunities

- T002 y T003 (tests US1) pueden escribirse en paralelo
- T007 y T008 (tests US3) pueden escribirse en paralelo
- US2 y US3 pueden trabajarse en paralelo una vez US1 está completa
- T009 y T010/T011 pueden iniciarse en paralelo (T009 solo toca docstring)

---

## Parallel Example: US1 + US3 en paralelo (tras T001)

```text
# Paralelo tras completar T001:
Task: T002 — test_two_saves_produce_distinct_paths
Task: T003 — test_saved_path_contains_valid_uuid4
Task: T007 — test_delete_removes_file
Task: T008 — test_legacy_path_readable

# Secuencial tras T002/T003 en ROJO:
Task: T004 — añadir import uuid
Task: T005 — modificar FileStore.save()
```

---

## Implementation Strategy

### MVP (User Story 1 únicamente)

1. Completar T001: crear archivo de tests
2. Completar T002–T003: escribir tests, confirmar ROJO
3. Completar T004–T005: implementar cambio en `storage.py`
4. **PARAR y VALIDAR**: `pytest backend/tests/unit/test_file_storage.py -v` → todo VERDE
5. Ejecutar T011: confirmar que tests de integración siguen pasando

### Entrega completa (todas las user stories)

1. T001 → T002–T003 (ROJO) → T004–T005 (impl) → VERDE = US1 lista
2. T006 (ROJO) → ya pasa con la impl de US1 = US2 lista
3. T007–T008 → ya pasan con impl de US1 = US3 lista
4. T009–T011 = Polish y confirmación final

---

## Notes

- [P] = archivos distintos o pruebas independientes, sin dependencias incompletas
- Total de tareas: **11**
- Cambios de producción: **2 líneas en 1 archivo** (`storage.py`)
- Cambios de tests: **4 funciones en 1 archivo nuevo** (`test_file_storage.py`)
- Sin migración de base de datos ni de archivos existentes
