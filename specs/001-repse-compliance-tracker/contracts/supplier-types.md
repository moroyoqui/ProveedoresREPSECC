# Contract: Supplier Types

Catálogo de tipos de proveedor (industrias) por tenant y sus requisitos. Cubre los FRs de la **Sección B + C + D del spec 003** (extendido) y consume las entidades `SupplierType`, `SupplierTypeDocumentRequirement` definidas en el data-model del spec 001.

## GET `/api/v1/supplier-types`

Lista los tipos de proveedor del tenant.

- **Auth**: requerida. **Roles**: cualquiera (consulta).
- **Query params**:
  - `status`: `active` | `archived` | `all` (default `active`).
  - `include_requirements`: `false` (default) o `true` para devolver la lista de requisitos por cada tipo.
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 1,
        "name": "Sin clasificar",
        "description": "Tipo por defecto sembrado por el sistema. Exige el catálogo canónico completo del tenant.",
        "origin": "system",
        "status": "active",
        "supplier_count": 4,
        "requirement_count": 10
      },
      {
        "id": 3,
        "name": "Construcción",
        "description": "Empresas de servicios de construcción.",
        "origin": "custom",
        "status": "active",
        "supplier_count": 12,
        "requirement_count": 7
      }
    ]
  }
  ```

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
- **Errores**:
  - `409 conflict` `name_exists` si ya existe el nombre en el tenant.
  - `400 validation_error`.

## GET `/api/v1/supplier-types/{type_id}`

Detalle del tipo con sus requisitos.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`:
  ```json
  {
    "id": 3,
    "name": "Construcción",
    "description": "Empresas de servicios de construcción.",
    "origin": "custom",
    "status": "active",
    "supplier_count": 12,
    "requirements": [
      {
        "id": 51,
        "document_type": { "id": 1, "slug": "opinion-sat", "name": "Opinión SAT", "periodicity": "monthly", "status": "active" },
        "periodicity_effective": "monthly",
        "periodicity_override": null,
        "status": "active",
        "created_at": "2026-05-16T10:00:00.000-06:00"
      },
      {
        "id": 52,
        "document_type": { "id": 4, "slug": "icsoe", "name": "ICSOE", "periodicity": "bimonthly", "status": "active" },
        "periodicity_effective": "bimonthly",
        "periodicity_override": null,
        "status": "active",
        "created_at": "2026-05-16T10:01:00.000-06:00"
      }
    ]
  }
  ```

## PATCH `/api/v1/supplier-types/{type_id}`

Actualiza nombre o descripción de un tipo personalizado. No aplica a `origin='system'`.

- **Auth**: requerida. **Roles**: admin.
- **Body**: subconjunto de `name`, `description`.
- **Respuesta** `200`.
- **Errores**:
  - `409 conflict` `name_exists`.
  - `403 system_type_immutable` si el tipo es `origin='system'`.

## POST `/api/v1/supplier-types/{type_id}/archive`

Archiva el tipo. Los proveedores asociados se conservan con etiqueta "tipo archivado".

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`: tipo con `status='archived'`.
- **Errores**: `403` si es `origin='system'`.

## POST `/api/v1/supplier-types/{type_id}/restore`

Reactiva un tipo archivado.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`.

## DELETE `/api/v1/supplier-types/{type_id}`

Elimina un tipo personalizado. Solo permitido si no tiene proveedores ni requisitos.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `204`.
- **Errores**:
  - `409 has_dependencies` con detalle `{ supplier_count, requirement_count }`.
  - `403 system_type_immutable`.

## Requisitos (asociaciones `SupplierType ↔ DocumentType`)

### GET `/api/v1/supplier-types/{type_id}/requirements`

Lista los requisitos activos del tipo.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`: misma forma del array `requirements` del detalle.

### POST `/api/v1/supplier-types/{type_id}/requirements`

Agrega un requisito al tipo.

- **Auth**: requerida. **Roles**: admin.
- **Body**:
  ```json
  {
    "document_type_id": 1,
    "periodicity_override": null
  }
  ```
- **Validaciones**:
  - `document_type_id`: existe, pertenece al tenant (canónico o personalizado), `status='active'`.
  - `periodicity_override`: opcional, uno de `monthly|bimonthly|annual|none`. Si NULL, hereda del DocumentType.
- **Respuesta** `201`: requisito creado.
- **Errores**:
  - `409 already_exists` si ya hay un requisito activo para ese par.
  - `409 doc_type_inactive` si el DocumentType está desactivado.
- **Side effect**: recalcula el cumplimiento de los proveedores con este `SupplierType`.

### PATCH `/api/v1/supplier-type-requirements/{requirement_id}`

Cambia el `periodicity_override` de un requisito.

- **Auth**: requerida. **Roles**: admin.
- **Body**: `{ "periodicity_override": "bimonthly" }` (o `null` para volver a herencia).
- **Respuesta** `200`.
- **Side effect**: recalcula el cumplimiento de los proveedores con este `SupplierType`. Los documentos previamente cargados se reevalúan con la nueva periodicidad efectiva.

### DELETE `/api/v1/supplier-type-requirements/{requirement_id}`

Retira un requisito (marca `status='retired'`). No se eliminan documentos cargados; se etiquetan como "requisito retirado".

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `204`.

## Plantillas por industria

### GET `/api/v1/supplier-type-templates`

Lista de plantillas canónicas mantenidas por el equipo del producto.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "slug": "construccion",
        "name": "Construcción",
        "description": "Empresas de servicios de construcción.",
        "required_document_type_slugs": [
          { "slug": "opinion-sat",       "suggested_periodicity": "monthly" },
          { "slug": "opinion-imss",      "suggested_periodicity": "monthly" },
          { "slug": "opinion-infonavit", "suggested_periodicity": "monthly" },
          { "slug": "icsoe",             "suggested_periodicity": "bimonthly" },
          { "slug": "sisub",             "suggested_periodicity": "bimonthly" },
          { "slug": "contrato-servicios","suggested_periodicity": "none" },
          { "slug": "cfdi-nomina",       "suggested_periodicity": "monthly" }
        ]
      }
    ]
  }
  ```

### POST `/api/v1/supplier-type-templates/{template_slug}/import`

Importa una plantilla al tenant.

- **Auth**: requerida. **Roles**: admin.
- **Body**:
  ```json
  {
    "name_override": null,
    "merge_strategy": "fail" 
  }
  ```
  - `name_override`: si NULL, usa el nombre canónico de la plantilla; si presente, usa ese nombre (útil para crear "Construcción (Privada)" diferenciada).
  - `merge_strategy`: `fail` (default — error si ya existe), `rename` (crea como "Nombre (N)" si choca), `merge` (si existe, agrega requisitos faltantes sin sobrescribir overrides).
- **Respuesta** `201` o `200` (merge):
  ```json
  {
    "supplier_type_id": 3,
    "created": ["periodicity:none for contrato-servicios"],
    "skipped_existing": ["opinion-sat", "opinion-imss"],
    "warnings": [
      { "code": "doc_type_inactive", "slug": "icsoe", "message": "ICSOE está desactivado en este tenant; el requisito quedará inactivo hasta reactivarlo." }
    ]
  }
  ```
- **Errores**:
  - `409 name_exists` si `merge_strategy='fail'` y ya hay un tipo con ese nombre.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /supplier-types, /supplier-types/{id} | ✅ | ✅ | ✅ |
| GET /supplier-types/{id}/requirements | ✅ | ✅ | ✅ |
| POST /supplier-types | 403 | 403 | ✅ |
| PATCH /supplier-types/{id} | 403 | 403 | ✅ |
| POST /supplier-types/{id}/archive | 403 | 403 | ✅ |
| POST /supplier-types/{id}/restore | 403 | 403 | ✅ |
| DELETE /supplier-types/{id} | 403 | 403 | ✅ |
| POST /supplier-types/{id}/requirements | 403 | 403 | ✅ |
| PATCH /supplier-type-requirements/{id} | 403 | 403 | ✅ |
| DELETE /supplier-type-requirements/{id} | 403 | 403 | ✅ |
| GET /supplier-type-templates | 403 | 403 | ✅ |
| POST /supplier-type-templates/{slug}/import | 403 | 403 | ✅ |
