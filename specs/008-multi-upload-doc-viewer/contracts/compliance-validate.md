# Contrato: Validación de Tipo de Documento

**Feature**: 008-multi-upload-doc-viewer — US6 (FR-020/FR-021) | **Date**: 2026-05-19

---

## Endpoint

```
POST /api/v1/suppliers/{supplier_id}/compliance/validate
```

**Autenticación**: JWT de sesión requerido  
**Autorización**: Rol `admin` o `manager` (`require_role`)

---

## Request

### Path params

| Param | Tipo | Descripción |
|---|---|---|
| `supplier_id` | integer | ID del proveedor |

### Body (JSON)

```json
{
  "document_type_id": 42,
  "coverage_period_start": "2026-01-01"
}
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `document_type_id` | integer | Sí | ID del tipo de documento a validar |
| `coverage_period_start` | string (ISO date) | No | `null` para requisitos de entrega única (periodicity=none) |

---

## Response — 200 OK

```json
{
  "status": "validated",
  "validated_at": "2026-05-19T14:30:00.000Z"
}
```

### Si el proveedor no pertenece al tenant

**404 Not Found**

```json
{
  "error": "not_found",
  "message": "Supplier not found"
}
```

### Si el usuario no tiene el rol requerido

**403 Forbidden**

```json
{
  "error": "forbidden",
  "message": "Insufficient role"
}
```

---

## Comportamiento

1. Verifica que `supplier.organization_id == user.organization_id`. Si no: 404.
2. Busca un registro existente en `compliance_cell_validations` con la clave `(organization_id, supplier_id, document_type_id, coverage_period_start)`.
3. Si existe: actualiza `validated_by` y `validated_at`.
4. Si no existe: crea el registro.
5. Hace `db.commit()`.
6. Devuelve 200 con `{status, validated_at}`.

**Idempotencia**: llamar al endpoint múltiples veces no duplica datos; solo actualiza el timestamp y el actor.

---

## Cambio en `GET /api/v1/suppliers/{id}/compliance`

El campo `type_validated: bool` se agrega a cada objeto `CellOut` en `monthly_requirements[*].cells[*]` y a los items de `one_time_requirements[*]` (si aplica). El frontend usa este campo para inicializar el estado del visualizador.

```json
{
  "monthly_requirements": [
    {
      "document_type": { "id": 42, "name": "IMSS", ... },
      "cells": [
        {
          "month": 1,
          "status": "validated",
          "document_id": 101,
          "document_count": 3,
          "coverage_period_start": "2026-01-01",
          "type_validated": true
        }
      ]
    }
  ]
}
```
