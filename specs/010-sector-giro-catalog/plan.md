# Implementation Plan: Catálogo de Sectores y Giros para Proveedores

**Branch**: `010-sector-giro-catalog` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from [./spec.md](./spec.md)

**Note**: Este archivo fue generado por `/speckit-plan`. Los artefactos complementarios ([research.md](./research.md), [data-model.md](./data-model.md), [contracts/catalog-sectors-giros.md](./contracts/catalog-sectors-giros.md)) son producidos por el mismo comando.

## Summary

Agregar dos catálogos de referencia globales — **Sectores** y **Giros** — al sistema ProveedoresREPSECC para clasificar a los proveedores con una jerarquía de dos niveles (sector → giro). Los catálogos son administrados por usuarios con rol `admin`, las asignaciones son opcionales en el proveedor, cualquier usuario interno puede filtrar la lista de proveedores por sector/giro, y los proveedores (rol `supplier`) pueden ver su clasificación desde su portal en modo solo lectura. Stack existente sin cambios: FastAPI + SQLAlchemy + MySQL (backend), React + Tailwind + TanStack Query (frontend).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.4 (frontend)

**Primary Dependencies**:
- **Backend**: FastAPI ≥0.110, SQLAlchemy 2.x, Alembic, Pydantic v2 — sin dependencias nuevas.
- **Frontend**: React 18, Vite, Tailwind CSS, TanStack Query v5, React Router, react-hook-form + Zod — sin dependencias nuevas.

**Storage**: MySQL 8.0 — dos tablas nuevas (`sectors`, `giros`) + dos columnas nuevas en `suppliers` (`sector_id`, `giro_id`). Migración `0007_add_sectors_giros`.

**Testing**:
- **Backend**: pytest + httpx (tests de contrato y autorización), factory_boy (fixtures).
- **Frontend**: Vitest + React Testing Library + MSW.

**Target Platform**: Linux x86_64/arm64, Docker Compose on-prem (sin cambios de infraestructura).

**Project Type**: Web app (monorepo frontend + backend separados).

**Performance Goals**:
- SC-003: listado de proveedores filtrado por sector/giro en <2 s para catálogos de hasta 5,000 proveedores (índices en `suppliers.sector_id` y `suppliers.giro_id`).
- SC-002: selector de giro en formulario responde inmediatamente al cambio de sector (filtrado client-side o query cacheada por TanStack Query).

**Constraints**:
- Catálogos `sectors` y `giros` son globales (sin `organization_id`). Ver justificación en Constitution Check y research.md.
- Los campos `sector_id`/`giro_id` en `suppliers` son nullable — compatibilidad total con registros existentes sin migración de datos.
- Hard delete exclusivo; sin soft-delete ni estado activo/inactivo.

**Scale/Scope**:
- Catálogos pequeños: estimado <200 sectores, <2,000 giros. No se requieren paginación ni búsqueda avanzada en los endpoints de catálogo.
- Impacto en `suppliers`: dos columnas nullable + dos índices. Sin overhead operativo relevante.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Justificación |
|-----------|--------|---------------|
| **I. Secure by Default** | ✅ Pass | Endpoints GET de catálogo: cualquier usuario autenticado. Endpoints POST/PATCH/DELETE: `require_role("admin")` igual que en `supplier_types/routes.py`. Portal: reutiliza la dependencia `require_supplier_session` existente de feature 009. Sin endpoints públicos nuevos. |
| **II. Multi-Tenant Data Isolation** | ✅ Pass (desviación justificada) | Las tablas `sectors` y `giros` no tienen `organization_id` — son datos de referencia del sistema, no datos de negocio del tenant. El aislamiento de tenant se preserva en `suppliers` (que ya tiene `organization_id` y `TenantOwned`). Los queries de filtrado de proveedores por sector/giro aplican el filtro tenant primero (`WHERE organization_id = ?`) y luego el filtro de clasificación. Ver Complexity Tracking. |
| **III. Test-First for Critical Paths** | ✅ Pass | Se escriben tests de contrato para autorización de todos los endpoints nuevos (admin-only para escritura) antes del merge. Test negativo: rol `manager` no puede hacer POST/DELETE en sectores/giros. Test de aislamiento: el filtro sector/giro en suppliers retorna solo los del tenant correcto. |
| **IV. Simplicity & YAGNI** | ✅ Pass | Sin nuevas dependencias. Sin soft-delete. Sin paginación en catálogos (pequeños). Sin versioning. Selector de giro en frontend filtrado por TanStack Query sobre datos ya cacheados (no un endpoint adicional). |

**Resultado del Constitution Check**: PASS (con desviación menor documentada en Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/010-sector-giro-catalog/
├── plan.md                   # Este archivo
├── research.md               # Decisiones de investigación
├── data-model.md             # Modelo de datos y migración
├── spec.md                   # Especificación de producto
├── contracts/
│   └── catalog-sectors-giros.md   # Contratos API
├── checklists/
│   └── requirements.md       # Checklist de calidad
└── tasks.md                  # Generado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── src/repse/
│   ├── sectors/                    ← NUEVO módulo
│   │   ├── __init__.py
│   │   ├── models.py               ← Sector (SQLAlchemy, sin TenantOwned)
│   │   ├── schemas.py              ← SectorIn, SectorOut
│   │   ├── service.py              ← CRUD + validaciones de dependencias
│   │   └── routes.py               ← GET/POST/PATCH/DELETE /sectors
│   ├── giros/                      ← NUEVO módulo
│   │   ├── __init__.py
│   │   ├── models.py               ← Giro (SQLAlchemy, sin TenantOwned)
│   │   ├── schemas.py              ← GiroIn, GiroOut, GiroBrief
│   │   ├── service.py              ← CRUD + validaciones de dependencias
│   │   └── routes.py               ← GET/POST/PATCH/DELETE /giros
│   ├── suppliers/                  ← MODIFICADO
│   │   ├── models.py               ← + sector_id, giro_id (nullable FKs)
│   │   ├── schemas.py              ← + SectorOut/GiroBrief en List/Detail; sector_id/giro_id en In/Patch
│   │   ├── service.py              ← + filtro sector_id/giro_id en list(); validación coherencia sector↔giro
│   │   └── routes.py               ← + query params ?sector_id &giro_id
│   ├── portal/                     ← MODIFICADO
│   │   └── routes.py               ← GET /portal/compliance retorna sector y giro del proveedor
│   └── main.py                     ← + include_router(sectors_router), include_router(giros_router)
└── alembic/versions/
    └── 0007_add_sectors_giros.py   ← NUEVA migración

frontend/
├── src/
│   ├── lib/api/
│   │   ├── sectors.ts              ← NUEVO: sectorsApi (list, create, update, delete)
│   │   └── giros.ts                ← NUEVO: girosApi (list, create, update, delete)
│   ├── pages/settings/catalogs/
│   │   ├── index.tsx               ← MODIFICADO: añadir links a Sectores y Giros
│   │   ├── sectors.tsx             ← NUEVA página: lista + crear + editar + eliminar sectores
│   │   └── giros.tsx               ← NUEVA página: lista + crear + editar + eliminar giros (selector de sector)
│   ├── pages/suppliers/
│   │   ├── list.tsx                ← MODIFICADO: + filtros sector/giro en toolbar
│   │   ├── new.tsx                 ← MODIFICADO: + SectorSelect + GiroSelect en cascada
│   │   └── edit.tsx                ← MODIFICADO: + SectorSelect + GiroSelect en cascada
│   ├── pages/suppliers/
│   │   └── detail.tsx              ← MODIFICADO: + fila sector/giro en la ficha
│   ├── pages/portal/
│   │   └── index.tsx               ← MODIFICADO: + bloque sector/giro (solo lectura)
│   └── app/
│       └── router.tsx              ← MODIFICADO: + rutas /settings/catalogs/sectors y /giros
```

**Structure Decision**: Web app (Option 2). Patrón existente del proyecto: backend bajo `backend/src/repse/` en módulos por dominio; frontend bajo `frontend/src/` en carpetas por página y componente.

## Complexity Tracking

| Violación | Por qué es necesaria | Alternativa más simple rechazada por |
|-----------|---------------------|--------------------------------------|
| Tablas `sectors` y `giros` sin `organization_id` (excepción al Principio II) | La spec requiere catálogos globales compartidos por todas las organizaciones. Un catálogo por-tenant haría imposible la uniformidad en clasificación entre clientes. | No hay alternativa más simple: per-tenant produce duplicación incontrolable; `org_id = NULL` como "global" genera ambigüedad en el ORM y queries más complejas. La excepción está contenida en dos tablas de referencia sin datos de negocio del cliente. |
