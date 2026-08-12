# Implementation Plan: Reportes Exportables de Cumplimiento

**Branch**: `004-compliance-reports` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-compliance-reports/spec.md`

## Summary

Permitir exportar el estado de cumplimiento de uno, varios o todos los proveedores de un tenant a **CSV** y **PDF**, con la opción de empaquetar los **archivos originales** en un **ZIP**. La generación es síncrona para alcances pequeños (≤ 50 proveedores / ≤ 1000 documentos) y **asíncrona** por encima de ese umbral, con seguimiento de estado in-app y descarga protegida por sesión durante al menos 24 horas. Cada exportación queda en bitácora y respeta estrictamente el aislamiento multi-tenant.

Enfoque técnico: un nuevo módulo backend `reports` que reutiliza el cálculo de estado de cumplimiento del spec 001 (`compliance`), renderiza CSV con la stdlib y PDF con **Jinja2 + WeasyPrint**, persiste cada solicitud en una tabla `export_request` (entidad "Solicitud de Exportación"), ejecuta los alcances grandes en un worker en proceso (sin introducir Celery/Redis), y almacena los archivos generados en disco local con nombre UUID (consistente con spec 012). El frontend agrega un diálogo de exportación reutilizable desde el detalle de proveedor y desde el listado filtrado, y hace polling del estado para los reportes asíncronos.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / React 18 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2 (backend); **WeasyPrint + Jinja2** (PDF), stdlib `csv` / `zipfile` / `zoneinfo` (CSV/ZIP/zona horaria); React 18 + Vite + Tailwind + TanStack Query v5 (frontend). Reutiliza el módulo `compliance` (estado calculado, FR-012 del spec 001) y `audit` (bitácora).

**Storage**: MySQL 8 para la tabla `export_request`; disco local para los archivos generados (CSV/PDF/ZIP) bajo un directorio de exportaciones con nombres UUID y expiración.

**Testing**: pytest (contract / integration / unit) desde la raíz con `backend/.venv`; Vitest/RTL para frontend según convención del repo.

**Target Platform**: Servidor Linux en Docker Compose on-prem detrás de Caddy.

**Project Type**: Web (backend FastAPI + frontend React).

**Performance Goals**: SC-002 ≤ 10 proveedores en < 5 s (síncrono); SC-003 50+ proveedores en < 5 min para el 90% de los casos (asíncrono).

**Constraints**: Descargas solo con sesión válida del tenant emisor (FR-007); cero fugas multi-tenant (FR-010, SC-004); enlaces válidos ≥ 24 h; fechas en zona horaria del tenant (FR-012); límite de tamaño total del ZIP a fijar (ver research).

**Scale/Scope**: Decenas a cientos de proveedores por tenant; umbral síncrono/asíncrono configurable (por defecto 50 proveedores o 1000 documentos).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Secure by Default (NON-NEGOTIABLE)**: ✅ Los endpoints de exportación y descarga requieren autenticación; los enlaces NO son públicos (FR-007). La descarga valida pertenencia al tenant emisor. Sin secretos en repo. Entrada (filtros, formato, alcance) validada con Pydantic en el borde.
- **II. Multi-Tenant Data Isolation**: ✅ Toda consulta de proveedores/documentos se filtra por `tenant_id` en la capa de datos; `export_request` lleva `tenant_id`. La descarga verifica que el solicitante pertenezca al tenant emisor. Tests negativos obligatorios (tenant A no puede descargar/leer export de tenant B) — SC-004, SC-006.
- **III. Test-First for Critical Paths**: ✅ La lógica de aislamiento y la autorización de descarga se cubren con tests antes del merge (contract + integration). El paridad reporte↔pantalla (FR-005/SC-001) también con test automatizado.
- **IV. Simplicity and Iteration (YAGNI)**: ✅ Se evita Celery/Redis: el modo asíncrono usa un worker en proceso respaldado por la tabla `export_request`. La notificación in-app se resuelve con polling de estado (sin infraestructura push). Cualquier complejidad añadida queda justificada en Complexity Tracking.

**Resultado**: PASS (sin violaciones que requieran justificación; ver Complexity Tracking vacío).

## Project Structure

### Documentation (this feature)

```text
specs/004-compliance-reports/
├── plan.md              # Este archivo (/speckit-plan)
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   └── reports-api.md
├── checklists/          # Existente
└── tasks.md             # Fase 2 (/speckit-tasks — NO lo crea /speckit-plan)
```

### Source Code (repository root)

```text
backend/src/repse/reports/
├── __init__.py
├── models.py            # ExportRequest (SQLAlchemy)
├── schemas.py           # Pydantic: ExportRequestCreate, ExportRequestOut, filtros, alcance
├── routes.py            # POST /reports/exports, GET /reports/exports/{id}, GET /reports/exports/{id}/download
├── service.py           # Orquestación: resolver alcance, decidir sync/async, persistir, bitácora
├── renderers/
│   ├── csv_renderer.py  # Filas (proveedor × documento) → CSV (stdlib csv)
│   ├── pdf_renderer.py  # Jinja2 + WeasyPrint
│   └── zip_packager.py  # Empaquetado con archivos originales (stdlib zipfile)
├── worker.py            # Procesamiento asíncrono en proceso + limpieza de expirados
└── templates/
    └── report.html      # Plantilla Jinja2 del PDF (encabezado tenant, tabla, leyenda)

backend/tests/
├── contract/test_reports_contract.py        # Esquemas de request/response de los endpoints
├── integration/test_reports_export.py        # CSV/PDF de un proveedor; paridad con datos
├── integration/test_reports_tenant_isolation.py  # Negativo multi-tenant (SC-004/SC-006)
├── integration/test_reports_async.py         # Umbral → async + polling de estado
└── unit/test_reports_renderers.py            # CSV/PDF/ZIP y zona horaria (FR-012)

frontend/src/
├── lib/api/reports.ts                        # Cliente: crear export, consultar estado, descargar
├── components/reports/ExportDialog.tsx        # Diálogo reutilizable (formato, alcance, ZIP)
└── pages/...                                  # Integración en detalle de proveedor y listado filtrado
```

**Structure Decision**: Web app con módulos verticales en `backend/src/repse/<módulo>/` (routes/service/schemas/models), siguiendo el patrón ya usado por `suppliers`, `documents`, `compliance`. Se añade el módulo `reports`. El frontend reutiliza su patrón `lib/api/<feature>.ts` + componente de diálogo, integrado en las pantallas existentes de proveedores.

## Complexity Tracking

> Sin violaciones de la constitución que requieran justificación. El modo asíncrono se implementa con un worker en proceso respaldado por tabla (no Celery/Redis), lo que mantiene el principio YAGNI; si en una fase posterior el volumen lo exige, se podrá sustituir por una cola dedicada sin cambiar el contrato de la API.
