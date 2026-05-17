# Contract: Users

Administración de usuarios del tenant. No expone perfiles de otras organizaciones.

## GET `/api/v1/users`

Lista usuarios del tenant.

- **Auth**: requerida.
- **Roles**: cualquiera.
- **Query params**: `cursor`, `limit` (1..100, default 20), `status` (active/disabled), `role`.
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 42,
        "email": "ana@empresa.mx",
        "display_name": "Ana López",
        "role": "admin",
        "status": "active",
        "last_login_at": "2026-05-15T08:12:33.456-06:00"
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
  ```

## POST `/api/v1/users`

Provisiona un nuevo usuario por correo. En v1 no envía invitación; cuando el usuario haga login con OIDC y su correo coincida, se asocia.

- **Auth**: requerida.
- **Roles**: admin.
- **Body**:
  ```json
  {
    "email": "nuevo@empresa.mx",
    "display_name": "Nuevo Usuario",
    "role": "manager"
  }
  ```
- **Respuesta** `201`: usuario creado en `status='active'`, sin `oidc_subject` aún.
- **Errores**:
  - `409 conflict` `email_exists` si ya hay usuario con ese correo en el tenant.

## PATCH `/api/v1/users/{user_id}`

Actualiza rol o status. No se puede cambiar el correo en v1.

- **Auth**: requerida.
- **Roles**: admin.
- **Body**: cualquiera de `role`, `status`, `display_name`.
- **Restricción**: un admin no puede bajarse a sí mismo a viewer si es el único admin activo del tenant (devuelve `409 last_admin`).
- **Respuesta** `200`: usuario actualizado.

## DELETE `/api/v1/users/{user_id}`

Soft-deletes y deshabilita al usuario. La fila se mantiene para preservar referencias en `audit_log` y `documents.uploaded_by`.

- **Auth**: requerida.
- **Roles**: admin.
- **Restricción**: igual que en PATCH (no se puede dejar al tenant sin admins).
- **Respuesta** `204`.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /users | ✅ | ✅ | ✅ |
| POST /users | 403 | 403 | ✅ |
| PATCH /users/{id} | 403 | 403 | ✅ |
| DELETE /users/{id} | 403 | 403 | ✅ |
