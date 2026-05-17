# API Contracts: Bóveda de Cumplimiento REPSE (Core)

Este directorio describe los **contratos HTTP** del backend FastAPI agrupados por dominio. La especificación formal se genera a partir del código (FastAPI emite OpenAPI 3.1 automáticamente en `/openapi.json` y la documentación interactiva en `/docs`). Estos `.md` definen el **contrato esperado** que el código DEBE cumplir.

## Convenciones generales

- **Base URL**: `/api/v1`. Cualquier breaking change incrementa `v2`.
- **Auth**: cookie de sesión `session` (set por el callback OIDC). Endpoints documentados como "auth required" rechazan 401 si la cookie no es válida.
- **Multi-tenant**: ningún endpoint recibe `organization_id` por parámetro. El tenant se deriva exclusivamente de la sesión. Recursos consultados que no pertenezcan al tenant del usuario responden **404**, no 403, para evitar enumerar IDs.
- **Errores**: respuesta JSON `{"error": {"code": "...", "message": "...", "details": {...}}}` con `code` enumerado:
  - `validation_error` (400) — falla Pydantic
  - `unauthenticated` (401)
  - `forbidden` (403) — rol insuficiente
  - `not_found` (404)
  - `conflict` (409) — duplicado, estado incompatible
  - `rate_limited` (429)
  - `internal_error` (500)
- **Paginación**: cursor-based. Parámetros `?cursor=<opaque>&limit=20`. Respuesta:
  ```json
  { "items": [...], "next_cursor": "...", "has_more": true }
  ```
- **Formatos**: fechas ISO-8601 (`2026-05-16`), timestamps con offset (`2026-05-16T15:23:11.123-06:00`), bytes en `bigint`.

## Dominios

| Archivo | Cobertura |
|---------|-----------|
| [auth.md](./auth.md) | Inicio de sesión OAuth/OIDC, callback, logout, perfil actual. |
| [organizations.md](./organizations.md) | Perfil y configuración del tenant (umbral de "por vencer", zona horaria). |
| [users.md](./users.md) | Listado, alta, baja y cambio de rol de usuarios del tenant. |
| [suppliers.md](./suppliers.md) | CRUD de proveedores (con asignación de tipo de proveedor). |
| [supplier-types.md](./supplier-types.md) | CRUD del catálogo de tipos de proveedor + asociaciones a tipos de documento + importación de plantillas por industria. |
| [document-types.md](./document-types.md) | Lectura del catálogo aplicable al tenant (canónico + personalizados activos). |
| [documents.md](./documents.md) | Subida, listado, descarga, sustitución, verificación manual y eliminación de documentos. |
| [audit.md](./audit.md) | Consulta de bitácora (read-only). |

Cada archivo lista los endpoints con verbo, ruta, payload de entrada, respuesta de éxito, errores comunes y reglas de autorización.

## Tests de contrato

Para cada endpoint, `tests/integration/contracts/test_<dominio>_contract.py` ejecuta:

1. **Forma de respuesta**: la respuesta valida contra el esquema Pydantic publicado.
2. **Auth required**: sin sesión retorna 401 con el envelope estándar de error.
3. **Multi-tenant negativo**: con sesión de Org B contra recurso de Org A → 404.
4. **Rol insuficiente**: viewer intentando POST/PUT/DELETE → 403.

Estos tests son parte del bloque de "test-first" exigido por la constitución (Principle III).
