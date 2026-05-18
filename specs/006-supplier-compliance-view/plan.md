# Implementation Plan: Vista de Cumplimiento Anual del Proveedor

**Branch**: `006-supplier-compliance-view` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from [./spec.md](./spec.md)

**Note**: Plan generado por `/speckit-plan`. Hereda el stack completo del [plan 001](../001-repse-compliance-tracker/plan.md). No introduce tecnología nueva. Todas las entidades necesarias existen en el [data-model 001](../001-repse-compliance-tracker/data-model.md).

## Summary

Añadir una vista de cuadrícula de cumplimiento anual accesible desde la pantalla de detalle de cada proveedor. El backend expone un nuevo endpoint `GET /api/v1/suppliers/{id}/compliance?year=YYYY` que calcula, para cada tipo de documento requerido por ese proveedor, el estado de cumplimiento por mes. El frontend reemplaza la tabla plana de "Documentos requeridos" en `SupplierDetailPage` con la cuadrícula de 12 columnas con esferas de color codificado. Los documentos sin periodicidad se muestran en una sección separada dentro de la misma página.

## Technical Context

Hereda íntegramente del [plan 001](../001-repse-compliance-tracker/plan.md). Sin dependencias nuevas.

**Language/Version**: Python 3.12 + TypeScript 5.4 (sin cambios).

**Primary Dependencies (nuevas)**: ninguna. La cuadrícula se implementa con CSS Grid + Tailwind nativo.

**Storage**: sin cambios de schema. La cuadrícula se calcula en el backend con una query JOIN sobre `documents`, `supplier_type_document_requirements`, `document_types` y `supplier_types`. Ver [data-model.md](./data-model.md).

**Testing**: pytest para la lógica de cálculo de celdas (unit tests de `cell_status`), httpx para el endpoint de compliance (integration con testcontainer MySQL). Vitest + React Testing Library para `ComplianceGrid`.

**Target Platform**: sin cambios.

**Project Type**: web app — extiende `backend/src/repse/` con nuevo módulo `compliance/`; frontend modifica `SupplierDetailPage` y agrega componentes en `components/suppliers/`.

**Performance Goals**:
- La cuadrícula completa (hasta 50 tipos de documento × 12 meses) carga en <2 s percibidos.
- La query de compliance debe resolver en <300 ms (p95) para un tenant con 500 proveedores y 50 000 documentos; el índice `ix_documents_org_supplier_type_period` ya cubre este acceso.

**Constraints**:
- Multi-tenant: el endpoint aplica el mismo `TenantOwned` filter que el resto del sistema; un proveedor de otro tenant devuelve 404.
- Solo lectura; no hay escrituras nuevas en este spec.
- El año por defecto es el año en curso; navegación a años anteriores fuera de scope.

**Scale/Scope**: mismo scope del 001. Por proveedor, la query toca a lo sumo `num_doc_types × 12` filas de `documents`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|-----------|--------|----------------|
| **I. Secure by Default** | ✅ Pass | `GET /compliance` requiere autenticación. `current_tenant` dependency garantiza que el proveedor pertenezca al tenant; de lo contrario 404. Sin datos adicionales más allá de los que ya exponía `GET /suppliers/{id}`. |
| **II. Multi-Tenant Data Isolation** | ✅ Pass | El servicio filtra por `organization_id` en todas las queries (mixin `TenantOwned`). Test negativo obligatorio: Org A solicita compliance de proveedor de Org B → 404. |
| **III. Test-First for Critical Paths** | ✅ Pass | La función `cell_status(...)` es el path crítico; se cubre con unit tests para los siete estados antes del merge. |
| **IV. Observability** | ✅ Pass | structlog emite `request_id`, `tenant_id`, `user_id` por middleware global. Sin escrituras → sin audit log nuevo. |
| **V. Simplicity & YAGNI** | ✅ Pass | Sin nuevas tablas, sin libs, sin worker, sin cache. Solo una query de lectura y un componente de grid en CSS/Tailwind. No se construye exportación, filtros por año ni comparativa entre proveedores. |

**Resultado**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/006-supplier-compliance-view/
├── spec.md
├── plan.md                       # Este archivo
├── research.md                   # Phase 0
├── data-model.md                 # Phase 1 (solo lógica computada, sin DDL nuevo)
├── quickstart.md                 # Phase 1
├── contracts/
│   └── compliance.md             # Contrato del nuevo endpoint
├── checklists/requirements.md
└── tasks.md                      # Phase 2 (NO creado aquí)
```

### Source Code (repository root)

```text
backend/
└── src/repse/
    ├── compliance/                       # NUEVO módulo
    │   ├── __init__.py
    │   ├── schemas.py                    # ComplianceGridOut, MonthlyRequirementOut, CellOut, OneTimeRequirementOut
    │   ├── service.py                    # get_annual_compliance(supplier_id, year, org_id)
    │   └── routes.py                     # GET /api/v1/suppliers/{supplier_id}/compliance
    └── main.py                           # AMPLIAR: registrar compliance router

frontend/
└── src/
    ├── pages/suppliers/
    │   └── detail.tsx                    # MODIFICAR: reemplazar tabla plana por ComplianceGrid + sección one-time
    ├── components/suppliers/
    │   ├── ComplianceGrid.tsx            # NUEVO: cuadrícula 12-col con sticky header de meses
    │   └── ComplianceCell.tsx            # NUEVO: esfera de color + tooltip de estado
    └── lib/api/
        └── index.ts                      # AMPLIAR: suppliersApi.compliance(id, year)
```

**Structure Decision**: nuevo módulo `compliance/` en el backend para mantener la lógica de cálculo de grid cohesiva y separada del módulo `suppliers/`. El frontend modifica la página de detalle existente (`/suppliers/:id`) en lugar de crear una nueva ruta, satisfaciendo el FR-001 del spec sin romper la navegación actual.

## Complexity Tracking

> No hay violaciones de la constitución. Sin entradas.
