# Contract: Document Types — Admin

Mutaciones sobre el catálogo de tipos de documento (FR-001..FR-012 del spec).

## POST `/api/v1/document-types`

Crea un tipo de documento personalizado del tenant.

- **Auth**: requerida. **Roles**: admin.
- **Body**:
  ```json
  {
    "name": "Constancia interna de seguridad e higiene",
    "description": "Documento interno emitido por el área de SST.",
    "periodicity": "bimonthly"
  }
  ```
- **Validaciones**:
  - `name`: 2..255 chars, único por tenant (canónico + custom), case-insensitive.
  - `periodicity`: `monthly` | `bimonthly` | `annual` | `none`.
- **Respuesta** `201`: tipo creado con `origin='custom'`, `status='active'`.
- **Errores**: `400 validation_error`, `409 name_exists`.
- **Side effects**: audit log `document_type.created`.

## PATCH `/api/v1/document-types/{id}`

Edita nombre, descripción o periodicidad de un tipo **personalizado**.

- **Auth**: requerida. **Roles**: admin.
- **Headers**: `If-Match: "<updated_at>"`.
- **Body**: subset de `name`, `description`, `periodicity`.
- **Respuesta** `200`: tipo actualizado.
- **Errores**:
  - `403 canonical_type_immutable` si el tipo es `origin='canonical'`.
  - `409 stale_update`.
  - `409 name_exists`.
- **Side effects**:
  - Audit log `document_type.updated` con prev/new.
  - Si cambia `periodicity`: el cambio aplica solo a documentos cargados **a partir de ahora**; los previos conservan su periodicidad efectiva original (FR-006).
  - Dispara recálculo de cumplimiento para todos los proveedores cuyos `SupplierType` referencien este tipo.

## DELETE `/api/v1/document-types/{id}`

Elimina un tipo **personalizado** sin documentos cargados ni asociaciones.

- **Auth**: requerida. **Roles**: admin.
- **Headers**: `If-Match: "<updated_at>"`.
- **Respuesta** `204`.
- **Errores**:
  - `403 canonical_type_immutable`.
  - `409 has_dependencies` con `{ documents_count, requirements_count }` → ofrecer archivar.

## POST `/api/v1/document-types/{id}/archive`

Archiva un tipo (canónico desactivar; personalizado archivar). Los documentos cargados sobre este tipo se conservan en histórico con etiqueta "tipo inactivo / archivado".

- **Auth**: requerida. **Roles**: admin.
- **Body** (opcional para canónicos):
  ```json
  { "reason": "No aplica a nuestra operación." }
  ```
- **Respuesta** `200`: tipo con `status='archived'` (personalizado) o `TenantDocumentTypeSetting.active=false` (canónico).
- **Errores**: si ya está archivado, `409 already_archived`.
- **Side effects**:
  - Audit log `document_type.archived` o `document_type.deactivated_canonical`.
  - Dispara recálculo de cumplimiento.

## POST `/api/v1/document-types/{id}/restore`

Reactiva un tipo previamente archivado / desactivado.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`.
- **Side effects**:
  - Audit log `document_type.restored` o `document_type.activated_canonical`.
  - Los documentos previamente cargados se reincorporan al cálculo.
  - Recalculo.

## GET `/api/v1/document-types/canonical-updates`

Lista tipos canónicos agregados al catálogo maestro **después** de la fecha de provisioning del tenant que aún están inactivos en el tenant.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 11,
        "slug": "cfdi-recibo-pago",
        "name": "CFDI de recibo de pago",
        "periodicity": "monthly",
        "available_since": "2026-09-01"
      }
    ]
  }
  ```
- **Side effects**: no muta nada. Solo lectura.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| POST /document-types | 403 | 403 | ✅ |
| PATCH /document-types/{id} | 403 | 403 | ✅ |
| DELETE /document-types/{id} | 403 | 403 | ✅ |
| POST /document-types/{id}/archive | 403 | 403 | ✅ |
| POST /document-types/{id}/restore | 403 | 403 | ✅ |
| GET /document-types/canonical-updates | 403 | 403 | ✅ |

Los endpoints de lectura (`GET /document-types`, `GET /document-types/{id}`) están en [001/contracts/document-types.md](../../001-repse-compliance-tracker/contracts/document-types.md).
