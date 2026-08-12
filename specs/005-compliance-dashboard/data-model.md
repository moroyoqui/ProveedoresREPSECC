# Data Model: Tablero de Control de Cumplimiento (005)

Este spec **no introduce entidades persistidas nuevas**. Reutiliza el modelo del spec 001/003/006. Define únicamente estructuras **en memoria** (DTO de respuesta + entrada de cache).

## Entidades reutilizadas (solo lectura)

| Entidad | Módulo | Uso en el tablero |
|---------|--------|-------------------|
| `Organization` (Tenant) | `organizations` | Define `organization_id` y zona horaria; alcance de todo el agregado. |
| `Supplier` | `suppliers` | Filas de la tabla resumen; filtro por proveedor; `status` (activo/inactivo); `supplier_type_id`. |
| `SupplierType` | `supplier_types` | Filtro "tipo de proveedor"; deriva los requisitos exigidos. |
| `SupplierTypeDocumentRequirement` | `supplier_types` | Define las celdas requeridas (solo `status = ACTIVE`); base del cálculo de "faltante". |
| `DocumentType` | `document_types` | Filtro "tipo de documento"; periodicidad; flag activo/archivado (los inactivos no cuentan como faltante, FR-014). |
| `Document` | `documents` | Documentos cargados; estado calculado, periodo cubierto, vencimiento. |

### Mapeo de estados (spec 001 FR-012 → tablero)

| Estado spec / `DocumentStatus` | Etiqueta del tablero | Cuenta como riesgo (FR-004a) |
|-------------------------------|----------------------|------------------------------|
| `valid` | vigente | No |
| `expiring_soon` | por vencer | No |
| `expired` | vencido | **Sí** |
| `missing` (derivado, no almacenado) | faltante | **Sí** |

> `missing` se deriva cuando existe una celda requerida (requisito activo × periodo aplicable del año) sin documento que la cubra. No se persiste.

## Estructuras en memoria

### `DashboardFilters` (entrada normalizada)

| Campo | Tipo | Default | Notas |
|-------|------|---------|-------|
| `year` | int | año en curso | Rango validado: `2020 ≤ year ≤ año_actual` (mismo guard que `compliance`). |
| `supplier_type_ids` | list[int] | [] (todos) | Multi-selección; incluye opción "Sin clasificar". |
| `document_type_ids` | list[int] | [] (todos los activos) | Multi-selección. |
| `supplier_ids` | list[int] | [] (todos) | Multi-selección (UI con búsqueda por nombre/RFC). |
| `statuses` | list[str] | [] (los 4) | Subconjunto de {vigente, por vencer, vencido, faltante}. |
| `include_inactive` | bool | false | Incluye proveedores inactivos (auditoría). |

La normalización (orden estable + dedupe) produce la porción de la clave de cache.

### `DashboardAggregate` (snapshot transitorio devuelto por el servicio)

Snapshot del conteo por categorías para los filtros aplicados. Calculado bajo demanda, opcionalmente servido desde cache (≤ 60 s). No se persiste.

- `filters: DashboardFilters` — eco de los filtros efectivos aplicados.
- `pie: list[PieSlice]` — una por estado.
  - `PieSlice { status: str, count: int, percent: int }` — los `percent` suman exactamente 100 (Hamilton, research §7).
- `by_document_type: list[DocTypeBar]`
  - `DocTypeBar { document_type_id: int, name: str, inactive: bool, valid: int, expiring_soon: int, expired: int, missing: int, compliance_percent: int }`
- `kpis: Kpis`
  - `Kpis { global_compliance_percent: int, active_suppliers: int, at_risk_suppliers: int, expiring_30d: int }`
  - `at_risk_suppliers` = proveedores **activos** con ≥1 documento `expired` o `missing` entre los requisitos exigidos por su `SupplierType` (FR-004a).
- `suppliers: list[SupplierRow]` — tabla resumen.
  - `SupplierRow { supplier_id: int, legal_name: str, rfc: str, supplier_type: str|null, status: str, compliance_percent: int, expired: int, missing: int }`
- `available_years: list[int]` — años con ≥1 documento cargado en el tenant (+ año en curso), máx. 10 hacia atrás (FR-005).
- `calculated_at: datetime` — hora local del tenant del cálculo (FR-021b).
- `empty_reason: str|null` — `"no_suppliers"` | `"no_data_for_filters"` | null (FR-018/FR-019).

### `CacheEntry` (interno)

| Campo | Tipo | Notas |
|-------|------|-------|
| clave | tuple | `(organization_id, tenant_version, filtros_normalizados)` |
| valor | `DashboardAggregate` | |
| `stored_at` | float (epoch) | TTL 60 s. |

El **contador de versión por tenant** (`dict[int, int]` en memoria) se incrementa ante los eventos de FR-021a; al cambiar, la clave deja de coincidir y la entrada caduca lógicamente (además del TTL).

## Reglas de validación

- `year` fuera de `[2020, año_actual]` → `400 invalid_year` (consistente con `compliance/routes.py`).
- `statuses` con valor desconocido → `400 invalid_status`.
- IDs de filtro que no pertenezcan al tenant → se ignoran silenciosamente (no filtran nada) en lugar de error, para tolerar URLs compartidas obsoletas. (Decisión de robustez; no expone datos de otro tenant porque todo va scoped por `organization_id`.)

## Transiciones de estado

No aplica: entidades reutilizadas son de solo lectura desde el tablero; el `DashboardAggregate` es inmutable una vez calculado.
