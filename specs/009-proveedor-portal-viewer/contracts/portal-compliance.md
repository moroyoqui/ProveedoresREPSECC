# Contract: Portal del Proveedor — Endpoints

**Feature**: 009-proveedor-portal-viewer  
**Base path**: `/api/v1/portal`  
**Auth**: Session cookie; rol `supplier` requerido en todos los endpoints.

---

## `GET /api/v1/portal/compliance`

Devuelve el grid de cumplimiento anual del proveedor asociado al usuario autenticado. El `supplier_id` se obtiene exclusivamente del payload de sesión del servidor; no se acepta ningún parámetro de identificación de proveedor en la petición.

### Query Parameters

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `year` | `integer` | No | Año de consulta. Default: año en curso. Rango: `2020 – año_actual`. |

### Headers

| Header | Valor |
|---|---|
| `Cookie` | `session=<token>` |

### Response `200 OK`

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

### Error Responses

| Status | Código de error | Condición |
|---|---|---|
| `401 Unauthorized` | `unauthenticated` | Sin cookie de sesión válida |
| `403 Forbidden` | `forbidden` | Rol ≠ `supplier` |
| `409 Conflict` | `supplier_not_linked` | Usuario con rol `supplier` sin `supplier_id` en sesión |
| `422 Unprocessable Entity` | `invalid_year` | Año fuera del rango `2020 – año_actual` |

### Authorization Model

```
session.role == "supplier"  AND  session.supplier_id IS NOT NULL
→ get_annual_compliance(db, supplier_id=session.supplier_id, organization_id=session.organization_id, year=year)
```

---

## `GET /api/v1/portal/history/{document_type_id}`

Devuelve el historial completo de documentos entregados para un tipo específico, del proveedor autenticado.

### Path Parameters

| Parámetro | Tipo | Descripción |
|---|---|---|
| `document_type_id` | `integer` | ID del tipo de documento |

### Response `200 OK`

```json
[
  {
    "id": 101,
    "version": 2,
    "is_latest": true,
    "coverage_period_start": "2026-01-01",
    "coverage_period_end": "2026-01-31",
    "due_date_effective": "2026-02-15",
    "status": "valid",
    "file_name_original": "nomina-enero-2026.pdf",
    "uploaded_by": 7,
    "created_at": "2026-01-20T10:30:00"
  }
]
```

### Error Responses

| Status | Código de error | Condición |
|---|---|---|
| `401 Unauthorized` | `unauthenticated` | Sin cookie de sesión válida |
| `403 Forbidden` | `forbidden` | Rol ≠ `supplier` |
| `409 Conflict` | `supplier_not_linked` | Sin `supplier_id` en sesión |

---

## `POST /api/v1/portal/upload`

Carga un documento para el propio proveedor autenticado. Solo disponible cuando la celda destino está en estado `missing`, `expired` o `pending`. No permite carga para períodos futuros.

### Request

`Content-Type: multipart/form-data`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `file` | `file` | Sí | Archivo a cargar |
| `document_type_id` | `integer` | Sí | ID del tipo de documento |
| `coverage_period_start` | `date` (YYYY-MM-DD) | Condicional | Requerido para tipos periódicos; omitir para tipos únicos (`periodicity = 'none'`) |

### Response `201 Created`

```json
{
  "id": 201,
  "document_type_id": 1,
  "coverage_period_start": "2026-05-01",
  "coverage_period_end": "2026-05-31",
  "status": "valid",
  "file_name_original": "nomina-mayo-2026.pdf",
  "file_size_bytes": 102400,
  "version": 1,
  "created_at": "2026-05-20T15:00:00"
}
```

### Error Responses

| Status | Código de error | Condición |
|---|---|---|
| `401 Unauthorized` | `unauthenticated` | Sin cookie de sesión válida |
| `403 Forbidden` | `forbidden` | Rol ≠ `supplier` |
| `409 Conflict` | `supplier_not_linked` | Sin `supplier_id` en sesión |
| `409 Conflict` | `upload_not_allowed` | Estado de celda es `validated`, `submitted` o `expiring_soon`; o período es futuro |
| `409 Conflict` | `max_files_reached` | Se alcanzó el límite de archivos del catálogo para ese tipo y período |
| `422 Unprocessable Entity` | `invalid_file_type` | Formato de archivo no aceptado para este tipo de documento |
| `422 Unprocessable Entity` | `file_too_large` | Archivo supera el tamaño máximo del catálogo |
| `422 Unprocessable Entity` | `future_period` | `coverage_period_start` es mayor al mes en curso |

### Authorization Model

```
session.role == "supplier"
AND session.supplier_id IS NOT NULL
AND coverage_period_start <= first_day_of_current_month()
AND cell_status(supplier_id, document_type_id, coverage_period_start) IN ('missing', 'expired', 'pending')
AND document_count_for_cell < document_type.max_files
→ create_document(db, supplier_id=session.supplier_id, organization_id=session.organization_id, ...)
```

---

## `POST /api/v1/portal/submit/{document_type_id}`

Envía el paquete de documentos de un tipo y período a revisión de contabilidad. Cambia el estado de la celda a `submitted` ("Pendiente de validación"). El botón "Enviar a validar" en el frontend invoca este endpoint.

### Path Parameters

| Parámetro | Tipo | Descripción |
|---|---|---|
| `document_type_id` | `integer` | ID del tipo de documento |

### Request Body

`Content-Type: application/json`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `coverage_period_start` | `date \| null` | Sí | Fecha de inicio del período; `null` para documentos únicos |

### Response `201 Created`

```json
{
  "submission_id": 10,
  "supplier_id": 42,
  "document_type_id": 1,
  "coverage_period_start": "2026-05-01",
  "submitted_at": "2026-05-20T15:05:00",
  "status": "pending"
}
```

### Error Responses

| Status | Código de error | Condición |
|---|---|---|
| `401 Unauthorized` | `unauthenticated` | Sin cookie de sesión válida |
| `403 Forbidden` | `forbidden` | Rol ≠ `supplier` |
| `409 Conflict` | `supplier_not_linked` | Sin `supplier_id` en sesión |
| `409 Conflict` | `no_documents_uploaded` | No hay documentos cargados para esa celda (FR-016) |
| `409 Conflict` | `already_submitted` | Ya existe una submission pendiente para esa celda (FR-018) |
| `409 Conflict` | `cell_not_submittable` | Estado de celda es `validated` o `expiring_soon` |

### Authorization Model

```
session.role == "supplier"
AND session.supplier_id IS NOT NULL
AND document_count_for_cell > 0
AND no active portal_submission with status='pending' for this cell
AND cell_status NOT IN ('validated', 'expiring_soon')
→ portal_submissions.insert(supplier_id, document_type_id, coverage_period_start, submitted_at=utcnow(), status='pending', pre_submission_status=current_status)
```

---

## `GET /api/v1/portal/submission/{document_type_id}`

Devuelve el motivo de rechazo de la última submission para una celda específica, cuando aplica.

### Query Parameters

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `coverage_period_start` | `date` | No | Período; omitir para documentos únicos |

### Response `200 OK`

```json
{
  "submission_id": 10,
  "status": "rejected",
  "submitted_at": "2026-05-20T15:05:00",
  "rejection_reason": "El RFC del archivo no coincide con el RFC del proveedor.",
  "rejected_at": "2026-05-21T09:00:00"
}
```

Devuelve `null` si no existe submission previa para esa celda.

### Error Responses

| Status | Código de error | Condición |
|---|---|---|
| `401 Unauthorized` | `unauthenticated` | Sin cookie de sesión válida |
| `403 Forbidden` | `forbidden` | Rol ≠ `supplier` |
| `409 Conflict` | `supplier_not_linked` | Sin `supplier_id` en sesión |

---

## Notas generales

- Ningún endpoint del portal acepta `supplier_id` como parámetro externo; siempre se extrae de la sesión.
- El portal no expone endpoints de eliminación ni modificación de documentos ya registrados.
- El campo `document_id` en `ComplianceGridOut` permite al frontend acceder al visor de documentos si se decide habilitar esa funcionalidad en una iteración futura.
- La interfaz de contabilidad para aprobar/rechazar submissions (que actualiza `portal_submissions.status`) es **fuera del alcance** de esta feature; será desarrollada en una feature independiente.
