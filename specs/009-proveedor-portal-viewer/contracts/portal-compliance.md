# Contract: Portal Compliance Endpoint

**Route**: `GET /api/v1/portal/compliance`  
**Auth**: Session cookie; role `supplier` required.  
**Feature**: 009-proveedor-portal-viewer

---

## Description

Devuelve el grid de cumplimiento anual del proveedor asociado al usuario autenticado. El `supplier_id` se obtiene exclusivamente del payload de sesión del servidor; no se acepta ningún parámetro de identificación de proveedor en la petición.

---

## Request

### Query Parameters

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `year` | `integer` | No | Año de consulta. Default: año en curso. Rango: `2020 – año_actual`. |

### Headers

| Header | Valor |
|---|---|
| `Cookie` | `session=<token>` |

---

## Response `200 OK`

Exactamente el mismo schema que `GET /api/v1/suppliers/{id}/compliance`.  
Tipo: `ComplianceGridOut`

```json
{
  "supplier": {
    "id": 42,
    "legal_name": "Empresa Proveedora S.A. de C.V.",
    "rfc": "EPR200101ABC",
    "supplier_type": { "id": 3, "name": "Servicios Generales" },
    "status": "active",
    "compliance_percent": 78
  },
  "year": 2026,
  "monthly_requirements": [
    {
      "document_type": {
        "id": 1,
        "slug": "nomina",
        "name": "Nómina",
        "periodicity": "monthly"
      },
      "cells": [
        {
          "month": 1,
          "status": "validated",
          "document_id": 101,
          "document_count": 2,
          "coverage_period_start": "2026-01-01",
          "type_validated": true
        }
      ]
    }
  ],
  "one_time_requirements": [
    {
      "document_type": {
        "id": 9,
        "slug": "acta-constitutiva",
        "name": "Acta Constitutiva",
        "periodicity": "none"
      },
      "status": "submitted",
      "document_id": 55,
      "due_date_effective": null
    }
  ]
}
```

---

## Error Responses

| Status | Código de error | Condición |
|---|---|---|
| `401 Unauthorized` | `unauthenticated` | Sin cookie de sesión válida |
| `403 Forbidden` | `forbidden` | Rol ≠ `supplier` |
| `409 Conflict` | `supplier_not_linked` | Usuario con rol `supplier` sin `supplier_id` en sesión (estado inválido) |
| `422 Unprocessable Entity` | `invalid_year` | Año fuera del rango `2020 – año_actual` |

---

## Authorization Model

```
session.role == "supplier"  AND  session.supplier_id IS NOT NULL
→  get_annual_compliance(db, supplier_id=session.supplier_id, organization_id=session.organization_id, year=year)
```

El endpoint **no** acepta un parámetro `supplier_id` externo. La identidad del proveedor es siempre la del usuario autenticado.

---

## Notes

- La respuesta es idéntica al endpoint admin para facilitar la reutilización del cliente frontend.
- El portal no expone endpoints de escritura; cualquier método distinto de `GET` retorna `405 Method Not Allowed`.
- El campo `document_id` permite al frontend abrir el visor de documentos existente si se decide exponer ese acceso al proveedor en una futura iteración.
