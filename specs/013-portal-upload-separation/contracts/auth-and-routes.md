# Contracts — 013 Portal Upload Separation

Los endpoints del portal **no cambian de URL ni de payload** (ver [data-model.md](../data-model.md)). El único contrato modificado es el login local; se documenta además el contrato de navegación.

## `POST /api/v1/auth/login` (modificado, retrocompatible)

### Request

```json
{
  "email": "user@example.com",
  "password": "********",
  "audience": "portal"
}
```

- `audience` (opcional): `"backoffice"` (default) | `"portal"`. Cualquier otro valor → 422.

### Responses

| Caso | Status | Body |
|---|---|---|
| Credenciales válidas y rol acorde a la audiencia | 200 | `{"status": "ok", "user_id": n, "organization_id": n}` + cookie de sesión |
| Credenciales inválidas | 422 | `{"code": "invalid_credentials", ...}` |
| Credenciales válidas pero rol no acorde a la audiencia (supplier en backoffice o no-supplier en portal) | 422 | **idéntico** a credenciales inválidas: `{"code": "invalid_credentials", ...}` |
| Email en más de una organización | 409 | `{"code": "ambiguous_user", ...}` (sin cambio) |

Regla de seguridad: la respuesta de audiencia equivocada DEBE ser byte-a-byte equivalente en código y estructura a la de credenciales inválidas (FR-013). La orientación a la puerta correcta vive en la UI de cada página de login como texto estático, no en la respuesta del servidor.

## Matriz de autorización de servicios (verificada por tests)

| Grupo de endpoints | admin/analyst | supplier |
|---|---|---|
| `/api/v1/portal/*` (read y write) | 403 | 200/201 |
| Administrativos (`/suppliers`, `/users`, `/documents`, `/document-types`, `/compliance`, etc.) | según rol | 403 |

## Contrato de navegación frontend

| Acción | Resultado esperado |
|---|---|
| GET `/portal` autenticado como supplier | redirect a `/portal/consulta` |
| GET `/portal/consulta` | vista solo lectura; cero controles de carga/envío (SC-001) |
| Celda `missing`/`expired` en consulta → acción "Ir a cargar" | `/portal/carga?type={document_type_id}&period={YYYY-MM-01}` con celda preseleccionada (FR-004) |
| GET `/portal/carga` sin celdas elegibles | mensaje positivo de cumplimiento (edge case spec) |
| supplier navega a ruta administrativa | redirect a `/portal/consulta` |
| admin/analyst navega a `/portal/*` | redirect a su área administrativa |
| GET `/portal/login` ya autenticado como supplier | redirect a `/portal/consulta` |
| Upload o submit exitoso en `/portal/carga` | invalidación de la query de compliance; al volver a consulta el estado está actualizado sin recarga manual (FR-011) |
