# Contract: Suppliers

CRUD de proveedores REPSE del tenant.

## GET `/api/v1/suppliers`

Lista proveedores del tenant.

- **Auth**: requerida. **Roles**: cualquiera.
- **Query params**:
  - `q`: búsqueda en `legal_name` o `rfc` (case-insensitive, substring).
  - `status`: `active` | `inactive` | `all` (default `active`).
  - `supplier_type_id`: filtro por tipo de proveedor (multi-valor permitido).
  - `cursor`, `limit` (default 20, máx 100).
  - `sort`: `legal_name` | `created_at` | `compliance_percent` (default `legal_name`).
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 12,
        "legal_name": "Servicios Industriales del Norte SA de CV",
        "rfc": "SIN9001022Y3",
        "supplier_type": { "id": 3, "name": "Construcción", "origin": "custom" },
        "contact_name": "Juan Pérez",
        "contact_email": "juanp@sin.mx",
        "status": "active",
        "compliance_percent": 78,
        "counts": { "valid": 5, "expiring_soon": 1, "expired": 1, "missing": 1 },
        "created_at": "2026-01-10T09:00:00.000-06:00"
      }
    ],
    "next_cursor": "eyJpZCI6MTJ9",
    "has_more": true
  }
  ```

## POST `/api/v1/suppliers`

Crea un proveedor.

- **Auth**: requerida. **Roles**: admin, manager.
- **Body**:
  ```json
  {
    "legal_name": "Servicios Industriales del Norte SA de CV",
    "rfc": "SIN9001022Y3",
    "supplier_type_id": 3,
    "contact_name": "Juan Pérez",
    "contact_email": "juanp@sin.mx",
    "contact_phone": "+52 81 1234 5678",
    "notes": null
  }
  ```
- **Validaciones**:
  - `rfc`: formato regex; único por tenant.
  - `legal_name`: 3..255 chars.
  - `supplier_type_id`: opcional en el payload. Si se omite, el sistema asigna automáticamente el `SupplierType` "Sin clasificar" del tenant. Si se incluye, debe pertenecer al tenant y estar `status='active'`.
  - Si `status='active'` (default), exigir al menos uno de `contact_email` o `contact_phone`.
- **Respuesta** `201`: proveedor creado.
- **Errores**:
  - `409 conflict` `rfc_exists` si ya existe el RFC en el tenant.
  - `400 validation_error`.

## GET `/api/v1/suppliers/{supplier_id}`

Detalle de un proveedor con su breakdown de documentos por tipo.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`:
  ```json
  {
    "id": 12,
    "legal_name": "Servicios Industriales del Norte SA de CV",
    "rfc": "SIN9001022Y3",
    "status": "active",
    "compliance_percent": 78,
    "documents_by_type": [
      {
        "document_type": {
          "id": 1,
          "slug": "opinion-sat",
          "name": "Opinión de cumplimiento SAT",
          "periodicity": "monthly"
        },
        "latest": {
          "id": 4521,
          "coverage_period_start": "2026-04-01",
          "coverage_period_end": "2026-04-30",
          "due_date_effective": "2026-05-31",
          "status": "valid",
          "verified": true,
          "uploaded_at": "2026-05-02T11:14:00.000-06:00"
        }
      },
      {
        "document_type": { "id": 2, "slug": "opinion-imss", "name": "Opinión IMSS", "periodicity": "monthly" },
        "latest": null,
        "status_override": "missing"
      }
    ],
    "created_at": "2026-01-10T09:00:00.000-06:00"
  }
  ```
- **Errores**: `404` si el proveedor no existe o pertenece a otro tenant.

## PATCH `/api/v1/suppliers/{supplier_id}`

Actualiza datos del proveedor (sin tocar RFC; RFC erróneo se corrige por reemplazo administrativo en v1).

- **Auth**: requerida. **Roles**: admin, manager.
- **Body**: cualquier subconjunto de `legal_name`, `supplier_type_id`, `contact_name`, `contact_email`, `contact_phone`, `status`, `notes`.
- **Side effect** al cambiar `supplier_type_id`: el sistema recalcula los documentos requeridos y el estado de cumplimiento del proveedor (FR-005a, FR-012b del spec 001) y registra la acción `supplier.type_changed` en bitácora con `prev_supplier_type_id` y `new_supplier_type_id`.
- **Respuesta** `200`.

## DELETE `/api/v1/suppliers/{supplier_id}`

Soft-delete (marca `status='inactive'` y `deleted_at`). El histórico de documentos se conserva.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `204`.

## POST `/api/v1/suppliers/{supplier_id}/reactivate`

Reactiva un proveedor previamente dado de baja.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`: proveedor con `status='active'`.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /suppliers, /suppliers/{id} | ✅ | ✅ | ✅ |
| POST /suppliers | 403 | ✅ | ✅ |
| PATCH /suppliers/{id} | 403 | ✅ | ✅ |
| DELETE /suppliers/{id} | 403 | 403 | ✅ |
| POST /suppliers/{id}/reactivate | 403 | 403 | ✅ |
