# Contract: Auth

Autenticación vía OAuth/OIDC contra Google y Microsoft. Sin contraseñas locales en v1.

## GET `/api/v1/auth/login/{provider}`

Inicia el flujo OIDC redirigiendo al consent screen del proveedor.

- **provider**: `google` | `microsoft`.
- **Query params**: `redirect_to` (opcional, URL relativa a la app a la que volver tras login).
- **Auth**: no requiere sesión.
- **Respuesta**: `302` con `Location: <authorize_url>` + cookie `oidc_state` (`HttpOnly`, `Secure`, `SameSite=Lax`).
- **Errores**: `400` si `provider` no es soportado.

## GET `/api/v1/auth/callback/{provider}`

Callback de OIDC. Intercambia el código por tokens, valida el `id_token`, crea/obtiene `User` y emite la cookie de sesión.

- **Query params**: `code`, `state` (debe coincidir con cookie `oidc_state`).
- **Auth**: no requiere sesión previa.
- **Respuesta**: `302` a `redirect_to` original (o `/` si no estaba) + cookie `session` (`HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, duración 12 h).
- **Errores**:
  - `400` `state_mismatch` si la cookie no coincide.
  - `409` `domain_not_provisioned` si el correo no pertenece a un dominio con organización registrada (en v1, onboarding manual).
  - `403` `user_disabled` si el `User` está en `status='disabled'`.
- **Rate limit**: 10 req/min/IP.

## POST `/api/v1/auth/logout`

Invalida la cookie de sesión y borra el contexto del usuario.

- **Auth**: requerida.
- **Respuesta**: `204`.
- **Side effects**: cookie `session` se reemplaza con `Max-Age=0`.

## GET `/api/v1/auth/me`

Devuelve el perfil del usuario actual.

- **Auth**: requerida.
- **Respuesta** `200`:
  ```json
  {
    "id": 42,
    "email": "ana@empresa.mx",
    "display_name": "Ana López",
    "role": "admin",
    "organization": {
      "id": 7,
      "legal_name": "Constructora REPSECC SA de CV",
      "rfc": "CRP120304XYZ",
      "expiring_soon_threshold_days": 15,
      "timezone": "America/Mexico_City"
    }
  }
  ```
- **Usado por**: el frontend tras montar para detectar si hay sesión y popular el contexto.

## Reglas de autorización

| Endpoint | Visitante anónimo | viewer | manager | admin |
|----------|-------------------|--------|---------|-------|
| GET /auth/login/* | ✅ | ✅ | ✅ | ✅ |
| GET /auth/callback/* | ✅ | ✅ | ✅ | ✅ |
| POST /auth/logout | 401 | ✅ | ✅ | ✅ |
| GET /auth/me | 401 | ✅ | ✅ | ✅ |
