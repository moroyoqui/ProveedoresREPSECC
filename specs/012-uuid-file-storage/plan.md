# Implementation Plan: UUID Suffix en Nombres de Archivo de Documentos

**Branch**: `012-uuid-file-storage` | **Date**: 2026-06-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-uuid-file-storage/spec.md`

## Summary

Añadir un sufijo UUID4 al nombre de cada archivo de documento almacenado en disco para garantizar unicidad absoluta de rutas, sin cambios de esquema de base de datos ni migración de archivos existentes. El único archivo de producción a modificar es `FileStore.save()` en `storage.py` (una línea de cambio efectivo).

## Technical Context

**Language/Version**: Python 3.12 (stdlib `uuid` module)

**Primary Dependencies**: Ninguna nueva — `uuid` es parte de la biblioteca estándar de Python

**Storage**: Disco local Docker (`/var/repse/uploads`); MySQL 8 para metadatos (campo `file_path VARCHAR(1024)` ya existente, sin cambio de esquema)

**Testing**: pytest; test unitario nuevo en `backend/tests/unit/test_file_storage.py`

**Target Platform**: Linux (Docker, ext4/xfs)

**Project Type**: Web service (FastAPI backend)

**Performance Goals**: Impacto despreciable — `uuid.uuid4()` genera ≈1M UUIDs/segundo; latencia de subida no se ve afectada

**Constraints**: Campo `file_path` soporta hasta 1024 caracteres; nueva ruta máxima ocupa ~75 caracteres

**Scale/Scope**: Cambio de una sola función (`FileStore.save`); cero callers externos construyen la ruta

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | ¿Aplica? | Evaluación |
|---|---|---|
| I. Secure by Default | Sí | Validación de path traversal existente permanece intacta; UUID4 no filtra información sensible |
| II. Multi-Tenant Isolation | No impacta | Segmentación `organization_id/supplier_id/document_id` no cambia |
| III. Test-First para rutas críticas | Sí | Test unitario añadido antes del cambio de producción |
| IV. YAGNI / Simplicidad | Sí | Cambio mínimo (1 línea); no se añaden abstracciones nuevas |

**Resultado**: PASS — sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/012-uuid-file-storage/
├── plan.md              # Este archivo (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (archivos afectados)

```text
backend/
├── src/repse/documents/
│   └── storage.py                    ← MODIFICAR: FileStore.save() (1 línea)
└── tests/unit/
    └── test_file_storage.py          ← CREAR: tests de unicidad y formato UUID
```

**Archivos NO modificados** (solo leen `file_path`; no construyen la ruta):
- `backend/src/repse/documents/service.py`
- `backend/src/repse/documents/routes.py`
- `backend/src/repse/portal/routes.py`
- `backend/src/repse/suppliers/type_change_service.py`

**Structure Decision**: Proyecto web (solo backend). Sin cambios en frontend ni en esquema de base de datos.

## Implementation Steps

### Step 1 — Modificar `FileStore.save()` (backend/src/repse/documents/storage.py)

Añadir `import uuid` al bloque de imports del módulo. Cambiar la construcción de `rel` (línea 58):

**Antes**:
```python
rel = f"{organization_id}/{supplier_id}/{document_id}/v{version}.{ext}"
```

**Después**:
```python
rel = f"{organization_id}/{supplier_id}/{document_id}/v{version}.{uuid.uuid4()}.{ext}"
```

### Step 2 — Crear test unitario (backend/tests/unit/test_file_storage.py)

Tests a implementar (usando `tmp_path` de pytest como `upload_root`):

1. **`test_two_saves_produce_distinct_paths`**: Dos llamadas con los mismos parámetros → `stored1.relative_path != stored2.relative_path`.
2. **`test_saved_path_contains_valid_uuid4`**: El segmento entre la versión y la extensión es un UUID4 válido (`uuid.UUID(segment, version=4)` no lanza).
3. **`test_open_returns_saved_content`**: Guarda y abre; verifica integridad del contenido.
4. **`test_delete_removes_file`**: Guarda y elimina; verifica que el archivo no existe en disco.

## Risks & Mitigations

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Archivos existentes (sin UUID) dejan de funcionar | Improbable | `open/delete` usan `doc.file_path` almacenado, no reconstruyen la ruta |
| UUID supera `VARCHAR(1024)` | Imposible | Ruta máxima ~75 chars; límite 1024 |
| Tests existentes fallan por cambio de formato | Bajo | Los mocks de `FileStore.save` en tests existentes devuelven rutas hardcoded |

## Complexity Tracking

> Sin violaciones de la Constitución — sección no aplica.
