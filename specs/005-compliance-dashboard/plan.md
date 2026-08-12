# Implementation Plan: Tablero de Control de Cumplimiento

**Branch**: `005-compliance-dashboard` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-compliance-dashboard/spec.md`

## Summary

Vista analítica de una sola pantalla que muestra el cumplimiento **agregado por tenant** de todos los proveedores, con cortes por año, tipo de proveedor, tipo de documento, proveedor y estado. Entrega: gráfico de pastel (desglose por estado), gráfico de barras (cumplimiento por tipo de documento), tira de KPIs y tabla resumen por proveedor, todo con drill-down al listado.

Enfoque técnico: un nuevo módulo backend `dashboard` que **agrega en servidor** reutilizando la lógica de estado ya existente (`documents.status.compute_status` y las reglas de requisitos por `SupplierType` del módulo `compliance`/spec 006), expuesto en un único endpoint de lectura `GET /api/v1/dashboard/compliance` con cache en proceso de 60 s e invalidación por contador de versión por tenant. El frontend añade una página `dashboard` (reemplazando el placeholder actual) que codifica filtros en la URL y renderiza los gráficos con **Recharts**.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.4 / React 18 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2 (backend); React 18, Vite 5, TanStack Query v5, Tailwind 3, react-router-dom 6, Recharts (nueva dependencia frontend para pastel/barras)

**Storage**: MySQL 8. Sin tablas nuevas; el tablero solo lee. Cache de agregados en memoria del proceso (dict con TTL), no persistido.

**Testing**: pytest (`backend/tests/{contract,integration,unit}`), vitest + Testing Library + Playwright (frontend)

**Target Platform**: Servicio web on-prem (Docker Compose + Caddy)

**Project Type**: Web application (backend FastAPI + frontend React)

**Performance Goals**: Vista por defecto < 2 s y cambio de filtro < 1.5 s en tenants con hasta 500 proveedores y 50 000 documentos (SC-001/SC-002). Agregación en servidor mediante consultas `GROUP BY`, sin transferir registros fila por fila.

**Constraints**: Aislamiento multi-tenant estricto (cero fugas en agregados, SC-006); suma del pastel exactamente 100% con redondeo controlado (SC-007); cero discrepancias con el detalle por proveedor (SC-003); frescura casi-real con cache ≤ 60 s e invalidación automática (FR-021/FR-021a). Zona horaria del tenant (por defecto America/Mexico_City) para "hoy" y los límites de año.

**Scale/Scope**: 1 endpoint de lectura nuevo + 1 página frontend. ~4 componentes de visualización (pastel, barras, KPIs, tabla). Sin migraciones de base de datos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Secure by Default**: El endpoint del tablero queda bajo el guard `_BACKOFFICE` (require_backoffice) y disponible a los tres roles del tenant (admin/gestor/consulta), sin acción mutante (solo lectura). Sin secretos nuevos. Entradas (filtros de query) validadas con Pydantic/Query. **PASS**
- **II. Multi-Tenant Data Isolation**: Todas las consultas de agregación se filtran por `organization_id` del usuario autenticado en la capa de datos (mixin `TenantOwned` + filtro explícito), igual que el módulo `compliance` existente. La clave de cache incluye `organization_id`. Test negativo obligatorio (tenant A no ve agregados de tenant B). **PASS**
- **III. Test-First for Critical Paths**: Se escriben primero los tests de aislamiento multi-tenant, de consistencia tablero↔detalle (SC-003) y de suma 100% del pastel (SC-007) antes de la implementación. **PASS**
- **IV. Simplicity and Iteration (YAGNI)**: Cache en proceso (no Redis) por ser despliegue single-backend on-prem; se reutiliza la lógica de estado existente en lugar de duplicarla; un solo endpoint agregado en vez de múltiples. La única dependencia nueva (Recharts) se justifica en research.md frente a SVG manual. Sin abstracciones especulativas. **PASS**

No hay violaciones que registrar en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-compliance-dashboard/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   └── dashboard-api.md
├── checklists/          # Existente (requirements)
└── tasks.md             # Generado por /speckit-tasks (no aquí)
```

### Source Code (repository root)

```text
backend/
├── src/repse/
│   ├── dashboard/                 # NUEVO módulo (agregación por tenant)
│   │   ├── __init__.py
│   │   ├── schemas.py             # DashboardOut, PieSlice, DocTypeBar, Kpis, SupplierRow, filtros
│   │   ├── service.py             # get_dashboard(...) — agregación + snapshot por año
│   │   └── routes.py              # GET /api/v1/dashboard/compliance
│   ├── common/
│   │   └── cache.py               # NUEVO: TenantVersionedTTLCache (o ampliar common existente)
│   ├── compliance/                # Reutilizado (reglas de requisitos por SupplierType)
│   ├── documents/                 # Reutilizado (status.py: compute_status con fecha ref.)
│   ├── suppliers/ supplier_types/ document_types/   # Reutilizados (modelos)
│   └── main.py                    # Registrar dashboard_router bajo _BACKOFFICE
└── tests/
    ├── contract/test_dashboard_contract.py        # forma de respuesta + filtros + roles
    ├── integration/test_dashboard_consistency.py  # SC-003 tablero↔detalle, SC-006 aislamiento
    └── unit/test_dashboard_aggregation.py         # SC-007 suma 100%, snapshot por año, KPIs

frontend/
├── src/
│   ├── pages/dashboard/
│   │   └── index.tsx              # Reemplaza placeholder: orquesta filtros (URL) + componentes
│   ├── components/dashboard/      # NUEVO
│   │   ├── StatusPieChart.tsx
│   │   ├── DocTypeBarChart.tsx
│   │   ├── KpiStrip.tsx
│   │   └── ComplianceSummaryTable.tsx
│   └── lib/api/dashboard.ts       # NUEVO: cliente TanStack Query del endpoint
└── tests/                         # vitest: render + drill-down + estados vacíos
```

**Structure Decision**: Web application (Opción 2). Se añade un módulo backend `dashboard` siguiendo el patrón existente (`models?/schemas/service/routes`; sin `models.py` porque no hay entidades nuevas) y se registra su router en `main.py` con el mismo guard `_BACKOFFICE` que los demás routers de back-office. En frontend se materializa la página `dashboard` ya enrutada y un set de componentes de visualización.

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
