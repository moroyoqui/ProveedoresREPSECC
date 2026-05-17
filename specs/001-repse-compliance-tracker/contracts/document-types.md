# Contract: Document Types (consumo)

Solo lectura del catálogo aplicable al tenant. La administración del catálogo (activar/desactivar canónicos, crear personalizados) vive en el spec [`003-document-catalog-admin`](../../003-document-catalog-admin/spec.md).

## GET `/api/v1/document-types`

Lista los tipos **activos** para el tenant (canónicos activos + personalizados activos), listos para asignar a un documento.

- **Auth**: requerida. **Roles**: cualquiera.
- **Query params**:
  - `include_inactive`: `false` (default) o `true` para incluir tipos desactivados/archivados (útil al editar histórico).
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 1,
        "slug": "opinion-sat",
        "name": "Opinión de cumplimiento SAT",
        "description": "Constancia 32-D del SAT...",
        "periodicity": "monthly",
        "origin": "canonical",
        "active": true
      },
      {
        "id": 102,
        "slug": "constancia-interna",
        "name": "Constancia interna de seguridad",
        "periodicity": "bimonthly",
        "origin": "custom",
        "active": true
      }
    ]
  }
  ```

## GET `/api/v1/document-types/{type_id}`

Detalle de un tipo (canónico o personalizado del tenant).

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta**: la misma estructura del item anterior, con `description` completa.
- **Errores**: `404` si no pertenece al tenant (cuando es `custom`) o no existe (canónico).

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /document-types | ✅ | ✅ | ✅ |
| GET /document-types/{id} | ✅ | ✅ | ✅ |
