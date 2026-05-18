# Contract: Supplier Compliance Grid

Vista de cumplimiento anual de un proveedor: cuadrícula de tipos de documento × meses.

## GET `/api/v1/suppliers/{supplier_id}/compliance`

Devuelve la cuadrícula de cumplimiento anual para el proveedor indicado.

- **Auth**: requerida. **Roles**: cualquiera (`viewer`, `manager`, `admin`).
- **Path param**: `supplier_id` — ID del proveedor (debe pertenecer al tenant del usuario autenticado).
- **Query params**:
  - `year` (int, opcional): año a visualizar. Default: año en curso (`date.today().year`). Rango permitido: `[2020, date.today().year]`.

### Respuesta `200`

```json
{
  "supplier": {
    "id": 12,
    "legal_name": "Servicios Industriales del Norte SA de CV",
    "rfc": "SIN9001022Y3",
    "supplier_type": { "id": 3, "name": "Construcción" },
    "status": "active",
    "compliance_percent": 78
  },
  "year": 2026,
  "monthly_requirements": [
    {
      "document_type": {
        "id": 1,
        "slug": "opinion-sat",
        "name": "Opinión de cumplimiento SAT",
        "periodicity": "monthly"
      },
      "cells": [
        {
          "month": 1,
          "status": "validated",
          "document_id": 4501,
          "coverage_period_start": "2026-01-01"
        },
        {
          "month": 2,
          "status": "submitted",
          "document_id": 4532,
          "coverage_period_start": "2026-02-01"
        },
        {
          "month": 3,
          "status": "missing",
          "document_id": null,
          "coverage_period_start": "2026-03-01"
        },
        {
          "month": 4,
          "status": "expired",
          "document_id": 4560,
          "coverage_period_start": "2026-04-01"
        },
        {
          "month": 5,
          "status": "pending",
          "document_id": null,
          "coverage_period_start": "2026-05-01"
        },
        {
          "month": 6,
          "status": "future",
          "document_id": null,
          "coverage_period_start": "2026-06-01"
        },
        { "month": 7,  "status": "future", "document_id": null, "coverage_period_start": "2026-07-01" },
        { "month": 8,  "status": "future", "document_id": null, "coverage_period_start": "2026-08-01" },
        { "month": 9,  "status": "future", "document_id": null, "coverage_period_start": "2026-09-01" },
        { "month": 10, "status": "future", "document_id": null, "coverage_period_start": "2026-10-01" },
        { "month": 11, "status": "future", "document_id": null, "coverage_period_start": "2026-11-01" },
        { "month": 12, "status": "future", "document_id": null, "coverage_period_start": "2026-12-01" }
      ]
    },
    {
      "document_type": {
        "id": 7,
        "slug": "opinion-imss",
        "name": "Opinión IMSS",
        "periodicity": "bimonthly"
      },
      "cells": [
        { "month": 1, "status": "validated", "document_id": 4600, "coverage_period_start": "2026-01-01" },
        { "month": 2, "status": "not_required", "document_id": null, "coverage_period_start": null },
        { "month": 3, "status": "validated", "document_id": 4610, "coverage_period_start": "2026-03-01" },
        { "month": 4, "status": "not_required", "document_id": null, "coverage_period_start": null },
        { "month": 5, "status": "pending",  "document_id": null, "coverage_period_start": "2026-05-01" },
        { "month": 6, "status": "not_required", "document_id": null, "coverage_period_start": null },
        { "month": 7, "status": "future", "document_id": null, "coverage_period_start": "2026-07-01" },
        { "month": 8, "status": "not_required", "document_id": null, "coverage_period_start": null },
        { "month": 9, "status": "future", "document_id": null, "coverage_period_start": "2026-09-01" },
        { "month": 10, "status": "not_required", "document_id": null, "coverage_period_start": null },
        { "month": 11, "status": "future", "document_id": null, "coverage_period_start": "2026-11-01" },
        { "month": 12, "status": "not_required", "document_id": null, "coverage_period_start": null }
      ]
    }
  ],
  "one_time_requirements": [
    {
      "document_type": {
        "id": 5,
        "slug": "acta-constitutiva",
        "name": "Acta Constitutiva",
        "periodicity": "none"
      },
      "status": "validated",
      "document_id": 1001,
      "due_date_effective": null
    },
    {
      "document_type": {
        "id": 6,
        "slug": "registro-repse",
        "name": "Registro REPSE",
        "periodicity": "none"
      },
      "status": "missing",
      "document_id": null,
      "due_date_effective": null
    }
  ]
}
```

### Valores posibles de `status` en `cells`

| Valor | Significado | Color UI |
|-------|-------------|----------|
| `validated` | Documento subido y verificado por admin | Verde |
| `submitted` | Documento subido, pendiente de verificación | Amarillo |
| `expired` | Documento subido pero vencido | Rojo oscuro |
| `missing` | Período pasado sin documento | Rojo |
| `pending` | Período actual sin documento (puede estar en plazo) | Gris claro |
| `future` | Período futuro, sin documento | Gris |
| `not_required` | Mes no aplica para la periodicidad del tipo | Vacío |

### Valores posibles de `status` en `one_time_requirements`

Subconjunto: `validated`, `submitted`, `expired`, `missing`.

### Errores

- `404 not_found` — el proveedor no existe o pertenece a otro tenant.
- `400 invalid_year` — el año está fuera del rango permitido.

### Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /suppliers/{id}/compliance | ✅ | ✅ | ✅ |
