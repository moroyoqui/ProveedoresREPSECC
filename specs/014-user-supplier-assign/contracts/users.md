# Contract: Users API (delta spec 014)

Solo se documenta el delta respecto al contrato existente en `specs/001-repse-compliance-tracker/`.

## GET /api/v1/users

### Response delta

`UserOut` añade un campo:

```json
{
  "id": 3,
  "email": "moroyoqui@gmail.com",
  "display_name": "Miguel",
  "role": "supplier",
  "status": "active",
  "supplier_id": 6,
  "supplier_name": "Juan Ruelas",
  "last_login_at": null
}
```

| Campo nuevo | Tipo | Nullable | Descripción |
|-------------|------|----------|-------------|
| `supplier_name` | string | sí | Nombre legal del proveedor; null si no tiene asignado |

Sin cambios en los endpoints POST/PATCH — el campo `supplier_id` ya era aceptado.

## Invariantes

- `supplier_name` es read-only; se escribe vía `supplier_id`.
- Si `role != "supplier"`, tanto `supplier_id` como `supplier_name` son `null`.
