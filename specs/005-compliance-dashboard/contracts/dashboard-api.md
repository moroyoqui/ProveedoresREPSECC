# Contrato API: Tablero de Cumplimiento (005)

Prefijo: `/api/v1`. Todos los endpoints van bajo el guard `_BACKOFFICE` (`require_backoffice`) y requieren sesión autenticada de un usuario del tenant (roles admin/gestor/consulta). Solo lectura. Aislamiento por `organization_id` del usuario; jamás se acepta `organization_id` por query.

---

## GET /api/v1/dashboard/compliance

Devuelve el agregado de cumplimiento del tenant para los filtros dados. Sirve desde cache (≤ 60 s) cuando aplica; el campo `calculated_at` indica la frescura.

### Query params

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `year` | int | año en curso | `2020 ≤ year ≤ año_actual`. |
| `supplier_type` | int (repetible) | — | `?supplier_type=1&supplier_type=4`. `0` = "Sin clasificar". |
| `document_type` | int (repetible) | — | Filtra tipos de documento. |
| `supplier` | int (repetible) | — | Filtra proveedores. |
| `status` | str (repetible) | — | Uno de `valid|expiring_soon|expired|missing`. |
| `include_inactive` | bool | false | Incluye proveedores inactivos. |

### 200 OK

```json
{
  "filters": {
    "year": 2026,
    "supplier_type_ids": [],
    "document_type_ids": [],
    "supplier_ids": [],
    "statuses": [],
    "include_inactive": false
  },
  "pie": [
    { "status": "valid",         "count": 412, "percent": 68 },
    { "status": "expiring_soon", "count": 54,  "percent": 9  },
    { "status": "expired",       "count": 79,  "percent": 13 },
    { "status": "missing",       "count": 61,  "percent": 10 }
  ],
  "by_document_type": [
    {
      "document_type_id": 3, "name": "Opinión SAT", "inactive": false,
      "valid": 40, "expiring_soon": 5, "expired": 8, "missing": 7,
      "compliance_percent": 72
    }
  ],
  "kpis": {
    "global_compliance_percent": 77,
    "active_suppliers": 128,
    "at_risk_suppliers": 34,
    "expiring_30d": 19
  },
  "suppliers": [
    {
      "supplier_id": 91, "legal_name": "ACME SA de CV", "rfc": "ACM010101AA1",
      "supplier_type": "Construcción", "status": "active",
      "compliance_percent": 64, "expired": 3, "missing": 2
    }
  ],
  "available_years": [2026, 2025, 2024],
  "calculated_at": "2026-06-14T09:31:00-06:00",
  "empty_reason": null
}
```

**Invariantes verificables**:
- `sum(pie[*].percent) == 100` siempre (SC-007), incluso con subconjuntos filtrados.
- `sum(pie[*].count)` == total de celdas evaluadas para los filtros.
- Conteos idénticos a los del endpoint de detalle `GET /api/v1/suppliers/{id}/compliance` para los mismos filtros (SC-003).
- Ningún registro de otro tenant aparece en `suppliers`, `pie`, `by_document_type` ni KPIs (SC-006).

### Estados vacíos (200 con `empty_reason`)

- Tenant sin proveedores → `empty_reason: "no_suppliers"`, listas vacías (FR-019).
- Filtros producen conjunto vacío → `empty_reason: "no_data_for_filters"` (FR-018).

### Errores

| Código | HTTP | Cuándo |
|--------|------|--------|
| `invalid_year` | 400 | `year` fuera de `[2020, año_actual]`. |
| `invalid_status` | 400 | valor de `status` desconocido. |
| `unauthorized` | 401 | sin sesión. |
| `forbidden` | 403 | rol no de back-office (p. ej. supplier). |

---

## Drill-down (responsabilidad del frontend)

No hay endpoint nuevo de drill-down. El cliente navega al listado existente propagando los filtros del tablero como query params + la dimensión seleccionada:

- Click porción del pastel → listado de documentos con `status=<estado>` + filtros activos (FR-015).
- Click barra → listado con `document_type=<id>` + filtros activos (FR-016).
- Click KPI "proveedores en riesgo" → listado de proveedores con `status=expired,missing` (FR-017).
- Click KPI "por vencer 30 días" → listado de documentos `status=expiring_soon` acotado a 30 días.

## Notas de implementación del contrato

- Tests de contrato (`backend/tests/contract/test_dashboard_contract.py`) verifican: forma de la respuesta, validación de params, suma 100% del pastel, y los 403 por rol supplier.
- El `calculated_at` se rinde en zona horaria del tenant (offset incluido).
