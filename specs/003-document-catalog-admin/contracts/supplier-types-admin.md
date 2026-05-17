# Contract: Supplier Types — Admin

Mutaciones del catálogo de tipos de proveedor (FR-013..FR-018 del spec). Los endpoints de lectura están en [001/contracts/supplier-types.md](../../001-repse-compliance-tracker/contracts/supplier-types.md).

## POST `/api/v1/supplier-types`

Crea un tipo de proveedor personalizado.

- **Auth**: requerida. **Roles**: admin.
- **Body**:
  ```json
  {
    "name": "Construcción",
    "description": "Empresas de servicios de construcción."
  }
  ```
- **Validaciones**:
  - `name`: 2..120 chars, único por tenant (case-insensitive).
- **Respuesta** `201`: tipo creado con `origin='custom'`, `status='active'`.
- **Errores**: `409 name_exists`, `400 validation_error`.
- **Side effects**: audit log `supplier_type.created`.

## PATCH `/api/v1/supplier-types/{id}`

Edita nombre o descripción de un tipo personalizado.

- **Auth**: requerida. **Roles**: admin.
- **Headers**: `If-Match: "<updated_at>"`.
- **Body**: subset de `name`, `description`.
- **Respuesta** `200`: tipo actualizado.
- **Errores**:
  - `403 system_type_immutable` si target es `origin='system'`.
  - `409 stale_update`, `409 name_exists`.
- **Side effects**: audit log `supplier_type.updated`.

## POST `/api/v1/supplier-types/{id}/archive`

Archiva un tipo personalizado. Los proveedores asociados se conservan con etiqueta "tipo archivado, reclasificar"; no se reasignan automáticamente (research §5).

- **Auth**: requerida. **Roles**: admin.
- **Body** (opcional): `{ "reason": "..." }`.
- **Respuesta** `200`: tipo con `status='archived'`. Cuerpo incluye `affected_suppliers_count`.
- **Errores**:
  - `403 system_type_immutable`.
  - `409 already_archived`.
- **Side effects**:
  - Audit log `supplier_type.archived` con `affected_suppliers_count`.
  - Genera notificación in-app al admin (vía spec 002 `notifications`) listando los proveedores a reclasificar.
  - Dispara recálculo de cumplimiento del tenant.

## POST `/api/v1/supplier-types/{id}/restore`

Reactiva un tipo archivado.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`.
- **Side effects**: audit log `supplier_type.restored`. Los proveedores siguen asociados; vuelven a contar al cumplimiento.

## DELETE `/api/v1/supplier-types/{id}`

Elimina un tipo personalizado solo si no tiene proveedores ni requisitos.

- **Auth**: requerida. **Roles**: admin.
- **Headers**: `If-Match: "<updated_at>"`.
- **Respuesta** `204`.
- **Errores**:
  - `403 system_type_immutable`.
  - `409 has_dependencies` con `{ supplier_count, requirement_count }` → ofrecer archivar.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| POST /supplier-types | 403 | 403 | ✅ |
| PATCH /supplier-types/{id} | 403 | 403 | ✅ |
| POST /supplier-types/{id}/archive | 403 | 403 | ✅ |
| POST /supplier-types/{id}/restore | 403 | 403 | ✅ |
| DELETE /supplier-types/{id} | 403 | 403 | ✅ |
