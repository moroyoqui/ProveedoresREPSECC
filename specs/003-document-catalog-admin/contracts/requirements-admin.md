# Contract: Requirements — Admin

Mutaciones sobre las asociaciones `SupplierType ↔ DocumentType` (FR-019..FR-022 del spec).

## POST `/api/v1/supplier-types/{type_id}/requirements`

Agrega un requisito al `SupplierType`.

- **Auth**: requerida. **Roles**: admin.
- **Body**:
  ```json
  {
    "document_type_id": 1,
    "periodicity_override": null
  }
  ```
- **Validaciones**:
  - `document_type_id`: existe en el tenant, `status='active'`.
  - `periodicity_override`: opcional, uno de `monthly|bimonthly|annual|none`. NULL = hereda.
- **Respuesta** `201`:
  ```json
  {
    "id": 51,
    "supplier_type_id": 3,
    "document_type": { "id": 1, "name": "Opinión SAT", "periodicity": "monthly", "origin": "canonical" },
    "periodicity_override": null,
    "periodicity_effective": "monthly",
    "status": "active",
    "created_at": "2026-05-17T10:00:00.000-06:00"
  }
  ```
- **Errores**:
  - `409 already_exists` si ya hay un requisito activo para ese par.
  - `409 doc_type_inactive` si el `DocumentType` está desactivado/archivado.
- **Side effects**: audit log `requirement.created`. Recalcula cumplimiento de proveedores con este `SupplierType`.

## PATCH `/api/v1/supplier-type-requirements/{req_id}`

Cambia `periodicity_override` de un requisito existente. Otros campos no son editables (para reemplazar el `DocumentType` se elimina y se crea otro).

- **Auth**: requerida. **Roles**: admin.
- **Headers**: `If-Match: "<updated_at>"`.
- **Body**:
  ```json
  { "periodicity_override": "bimonthly" }
  ```
  o `{ "periodicity_override": null }` para volver a heredar.
- **Respuesta** `200`: requisito actualizado.
- **Errores**: `409 stale_update`.
- **Side effects**:
  - Audit log `requirement.periodicity_changed` con prev/new.
  - Recalcula cumplimiento de proveedores con este `SupplierType`; los documentos previamente cargados se reevalúan con la nueva periodicidad efectiva.

## DELETE `/api/v1/supplier-type-requirements/{req_id}`

Retira un requisito (marca `status='retired'`). Los documentos cargados se conservan en histórico con etiqueta "requisito retirado".

- **Auth**: requerida. **Roles**: admin.
- **Headers**: `If-Match: "<updated_at>"`.
- **Respuesta** `204`.
- **Side effects**:
  - Audit log `requirement.retired`.
  - Recalcula cumplimiento.

## POST `/api/v1/supplier-type-requirements/{req_id}/restore`

Reactiva un requisito retirado. Si entre tanto el `DocumentType` quedó desactivado, responde `409 doc_type_inactive`.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`.
- **Side effects**: audit log `requirement.restored`. Recalcula.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| POST /supplier-types/{id}/requirements | 403 | 403 | ✅ |
| PATCH /supplier-type-requirements/{id} | 403 | 403 | ✅ |
| DELETE /supplier-type-requirements/{id} | 403 | 403 | ✅ |
| POST /supplier-type-requirements/{id}/restore | 403 | 403 | ✅ |

Lectura (`GET /supplier-types/{id}/requirements`) está en [001/contracts/supplier-types.md](../../001-repse-compliance-tracker/contracts/supplier-types.md).
