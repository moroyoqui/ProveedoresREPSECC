# Quickstart: Tablero de Control de Cumplimiento (005)

Guía mínima para implementar y validar el feature una vez generadas las tareas.

## Requisitos previos

- Dependencias de los specs 001/003/006 presentes en la rama (entidades `Supplier`, `Document`, `SupplierType`, `DocumentType`, `SupplierTypeDocumentRequirement` y el módulo `compliance`).
- Backend: `backend/.venv` (Python 3.13) activo + Docker para MySQL. Tests con `pytest` desde la raíz.
- Frontend: `npm install --legacy-peer-deps` (incluye la nueva dependencia `recharts`).

## Backend — pasos

1. Crear módulo `backend/src/repse/dashboard/` con `__init__.py`, `schemas.py`, `service.py`, `routes.py`.
2. En `service.py`, implementar `get_dashboard(db, *, organization_id, filters, today=None)`:
   - Resolver `ref_date` según el año (hoy vs. 31-dic del año pasado, zona horaria del tenant — research §3/§5).
   - Derivar celdas requeridas desde `SupplierTypeDocumentRequirement` activos × `DocumentType` activos, expandidas por periodicidad (reutilizar helpers de `compliance.service`: `applicable_months`, `effective_periodicity`).
   - Agregar con `GROUP BY` scoped por `organization_id`; calcular estado con `documents.status.compute_status`.
   - Aplicar redondeo Hamilton al pastel (suma 100).
3. Crear `common/cache.py` con un cache TTL (60 s) + contador de versión por tenant; exponer `bump_tenant_version(organization_id)`.
4. Conectar `bump_tenant_version` en los puntos de mutación (FR-021a): servicios de `documents` (alta/edición/borrado), catálogo de `document_types` (activar/desactivar/archivar), `suppliers` (alta/baja/reactivación) y cambios de configuración de estado.
5. Registrar el router en `main.py`:
   ```python
   from repse.dashboard.routes import router as dashboard_router
   app.include_router(dashboard_router, prefix=f"{API_PREFIX}/dashboard", tags=["dashboard"], dependencies=_BACKOFFICE)
   ```

## Frontend — pasos

1. `npm i recharts --legacy-peer-deps`.
2. `src/lib/api/dashboard.ts`: hook `useDashboard(filters)` con TanStack Query (query key = filtros).
3. Componentes en `src/components/dashboard/`: `StatusPieChart`, `DocTypeBarChart`, `KpiStrip`, `ComplianceSummaryTable` (con handlers de drill-down que navegan al listado propagando filtros).
4. `src/pages/dashboard/index.tsx`: leer/escribir filtros con `useSearchParams`, botón "Limpiar filtros", indicador de `calculated_at`, estados vacíos (`empty_reason`).

## Validación (criterios de aceptación)

```bash
# Backend
pytest backend/tests/unit/test_dashboard_aggregation.py        # SC-007 suma 100%, snapshot año, KPIs
pytest backend/tests/integration/test_dashboard_consistency.py # SC-003 tablero↔detalle, SC-006 aislamiento
pytest backend/tests/contract/test_dashboard_contract.py       # forma + validación + 403 rol supplier

# Frontend
cd frontend && npm run test:run
```

Checklist manual:
- [ ] Vista por defecto carga año en curso sin filtros, con pastel + barras + KPIs + tabla (FR-002/FR-003).
- [ ] Cambiar año a uno pasado recalcula al cierre 31-dic de ese año (FR-012).
- [ ] Filtrar por tipo de documento + estado mantiene pastel sumando 100% del subconjunto (FR-007/SC-007).
- [ ] Recargar/compartir URL reconstruye filtros (FR-008); "Limpiar filtros" vuelve al default (FR-009).
- [ ] Drill-down lleva al listado con filtros aplicados (FR-015/016/017).
- [ ] Tenant sin proveedores muestra estado de bienvenida (FR-019); filtro vacío muestra mensaje, no gráfico vacío (FR-018).
- [ ] Indicador de última actualización en zona horaria del tenant (FR-021b).
- [ ] Tenant A no ve datos de tenant B en ningún agregado (SC-006).
