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

## GET `/api/v1/suppliers/{supplier_id}/type-change-preview`

Vista previa del impacto destructivo de cambiar el `SupplierType` del proveedor (FR-005b spec 001).

- **Auth**: requerida. **Roles**: admin, manager.
- **Query params**:
  - `supplier_type_id` (requerido, entero ≥ 1): identificador del tipo objetivo.
- **Semántica**: identifica los documentos del proveedor cuya `due_date_effective` cae dentro del año natural en curso (zona horaria del tenant). Esos documentos serían eliminados permanentemente al aplicar el cambio.
- **Respuesta** `200`:
  ```json
  {
    "requires_confirmation": true,
    "affected_count": 2,
    "affected_documents": [
      {
        "id": 4521,
        "document_type": "Opinión de cumplimiento SAT",
        "coverage_period": "2026-04-01 a 2026-04-30",
        "due_date_effective": "2026-05-31"
      },
      {
        "id": 4811,
        "document_type": "Opinión IMSS",
        "coverage_period": "2026-03-01 a 2026-03-31",
        "due_date_effective": "2026-04-30"
      }
    ]
  }
  ```
- **Errores**:
  - `404 not_found` si el proveedor o el `supplier_type_id` no pertenecen al tenant.
  - `400 validation_error` si el `SupplierType` está archivado.

## PATCH `/api/v1/suppliers/{supplier_id}`

Actualiza datos del proveedor (sin tocar RFC; RFC erróneo se corrige por reemplazo administrativo en v1).

- **Auth**: requerida. **Roles**: admin, manager.
- **Body**: cualquier subconjunto de `legal_name`, `supplier_type_id`, `contact_name`, `contact_email`, `contact_phone`, `status`, `notes`, `confirmation_text`.
  - `confirmation_text` (opcional): texto literal `"eliminar"` (comparación case-insensitive con `trim`). Requerido cuando el cambio de `supplier_type_id` afectará documentos con `due_date_effective` dentro del año en curso.
- **Side effect** al cambiar `supplier_type_id`:
  - Si **no hay documentos afectados**: se aplica el nuevo tipo de inmediato; el sistema recalcula los documentos requeridos y el estado de cumplimiento del proveedor (FR-005a, FR-012b spec 001) y registra `supplier.type_changed` (`destructive=false`).
  - Si **hay documentos afectados** (al menos uno con `due_date_effective` en el año en curso) y el cliente NO envía `confirmation_text`: la operación se rechaza con `409 confirmation_required` incluyendo `affected_documents` en `error.details`. El estado del proveedor no cambia.
  - Si **hay documentos afectados** y `confirmation_text` no coincide con `"eliminar"`: la operación se rechaza con `422 invalid_confirmation`.
  - Si **hay documentos afectados** y `confirmation_text` coincide: la transacción (a) elimina permanentemente los registros + archivos de los documentos afectados, (b) aplica el nuevo `supplier_type_id`, (c) registra `document.deleted_by_supplier_type_change` por cada documento eliminado y `supplier.type_changed` (`destructive=true`).
- **Respuesta** `200`: detalle del proveedor con el nuevo tipo y `documents_by_type` recalculado.
- **Errores**:
  - `409 confirmation_required` cuando el cambio destructivo requiere confirmación.
  - `422 invalid_confirmation` cuando `confirmation_text` no coincide.

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
