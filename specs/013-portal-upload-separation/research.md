# Research — 013 Portal Upload Separation

**Date**: 2026-06-11 · **Spec**: [spec.md](spec.md)

Estado actual relevante (verificado en código):

- Login único en `frontend/src/pages/auth/login.tsx` (`/login`), que llama `POST /api/v1/auth/login` (`backend/src/repse/auth/routes.py:164`) sin distinción de audiencia; tras autenticarse, `RootRedirect` (`frontend/src/app/router.tsx:56`) redirige por rol (`supplier → /portal`).
- `AppShell` (`frontend/src/components/layout/AppShell.tsx`) es un layout compartido con una rama condicional para supplier (un solo link "Mi documentación").
- El portal es una sola página (`frontend/src/pages/portal/index.tsx`, 253 líneas) que mezcla grid de consulta, historial, diálogo de carga y botón de envío.
- Backend: un solo router `repse/portal/routes.py` montado en `/api/v1/portal` con 3 GET (consulta) y 2 POST (carga/envío), todos con `require_role(Role.SUPPLIER)`.

## Decision 1 — Rutas separadas `/portal/consulta` y `/portal/carga`

**Decision**: Dividir `PortalPage` en dos páginas bajo rutas hermanas: `/portal/consulta` (solo lectura: grid, alertas, historial, motivo de rechazo) y `/portal/carga` (lista de celdas elegibles + diálogo de carga + envío a validación). `/portal` redirige con `Navigate replace` a `/portal/consulta` (cubre FR-006 y marcadores antiguos).

**Rationale**: Cumple FR-001/FR-002/FR-003 con el mínimo de cambios; los componentes existentes (`ComplianceGrid` del portal, `UploadPortalDialog`, `SubmitValidationButton`, `RejectionReasonBanner`) se reparten entre las dos páginas sin reescribirse.

**Alternatives considered**: Tabs dentro de una misma página — rechazado: no cumple "totalmente separadas" (FR-002, la pantalla de consulta no debe contener controles de carga) ni la navegación de primer nivel (FR-005).

## Decision 2 — `PortalShell` propio en lugar de la rama supplier de `AppShell`

**Decision**: Crear `frontend/src/components/layout/PortalShell.tsx` con menú exclusivo (Consulta, Carga, cerrar sesión) e identidad visual del portal. Las rutas de supplier se montan bajo `PortalShell`; se elimina la rama condicional supplier de `AppShell`, que queda solo para back-office.

**Rationale**: FR-014 exige menú independiente sin opciones administrativas; mantener el condicional dentro de `AppShell` acopla ambos mundos y ya generó la mezcla que el usuario quiere eliminar.

**Alternatives considered**: Mantener `AppShell` con NAV filtrado por rol — rechazado: la pantalla compartiría identidad y estructura del back-office, contrario a US4.

## Decision 3 — Login dedicado del portal en `/portal/login` con campo `audience`

**Decision**: Nueva página `frontend/src/pages/portal/login.tsx` en ruta `/portal/login` (solo correo y contraseña, identidad del portal). `POST /auth/login` acepta un campo opcional `audience: "backoffice" | "portal"` (default `"backoffice"`, retrocompatible). Tras verificar credenciales, si el rol no corresponde a la audiencia, el backend responde el mismo error genérico `invalid_credentials` que para credenciales inválidas.

**Rationale**: FR-012/FR-013. Reutiliza el mecanismo de sesión existente (`SessionManager`, cookie firmada) sin sistema de cuentas paralelo (FR-015). Responder el mismo error en mismatch evita revelar la validez de las credenciales (requisito explícito de FR-013); la orientación a "la puerta correcta" se da de forma estática en la UI: cada página de login muestra un enlace permanente a la otra entrada ("¿Eres proveedor? Entra por el portal" / "¿Personal administrativo? Entra por aquí").

**Alternatives considered**: (a) Endpoint separado `POST /auth/portal/login` — rechazado: duplica la lógica de lookup/verify sin beneficio; un campo de audiencia es más simple. (b) Código de error `wrong_entry` tras credenciales válidas — rechazado: revela que las credenciales son correctas, violando FR-013.

## Decision 4 — OIDC (Google/Microsoft) permanece solo en la entrada administrativa

**Decision**: Los botones OIDC siguen únicamente en `/login`. Si una cuenta supplier completa el flujo OIDC, el `callback` emite sesión como hoy y el router la lleva a `/portal/consulta`; no se agrega gating de audiencia al callback en v1.

**Rationale**: YAGNI (Constitución IV): los proveedores se autentican con correo/contraseña local (así los crea el admin en 009); endurecer el callback OIDC no aporta a ningún criterio de aceptación y agrandaría el cambio en una ruta crítica.

**Alternatives considered**: Bloquear suppliers en el callback OIDC — rechazado por alcance; queda anotado como deuda menor en quickstart.

## Decision 5 — Segregación de servicios por naturaleza: routers `read` y `write`

**Decision**: Dividir `repse/portal/routes.py` en `routes_read.py` (GET `/compliance`, `/history/{id}`, `/submission/{id}` — sin escritura alguna a BD) y `routes_write.py` (POST `/upload`, `/submit/{id}`). Ambos se montan bajo el mismo prefijo `/api/v1/portal` (las URLs no cambian; no se rompe el frontend existente durante la transición). El helper `_check_upload_allowed` vive en `routes_write.py`.

**Rationale**: FR-009 exige que las operaciones de consulta sean de solo lectura y verificables; la separación por módulo permite un test estructural ("ningún endpoint de `routes_read` usa métodos distintos de GET ni hace `db.add/commit`"). Mantener URLs evita migración del cliente y cumple FR-007 (reglas de negocio intactas).

**Alternatives considered**: Prefijos nuevos `/portal/consulta/*` y `/portal/carga/*` — rechazado: rompe contratos existentes sin valor para el usuario; la segregación exigida es de operaciones, no de nombres de URL.

## Decision 6 — Exclusión proveedor/back-office en servicios ya cubierta; se refuerza con tests

**Decision**: No se cambia el modelo de autorización: los endpoints del portal ya exigen `require_role(Role.SUPPLIER)` y los administrativos exigen roles no-supplier. Se agregan/extienden tests (`test_portal_auth.py`, nuevo `test_auth_entry.py`) que recorren los endpoints administrativos con credencial supplier esperando 403, y el login con audiencia cruzada esperando el error genérico.

**Rationale**: FR-008/SC-003 piden garantía verificable, no re-arquitectura; Constitución III exige estos tests antes del merge.

**Alternatives considered**: Middleware de audiencia por prefijo de URL — rechazado: redundante con `require_role` existente (YAGNI).

## Decision 7 — Sesiones existentes y estado tras carga

**Decision**: El payload de sesión no cambia; sesiones activas previas siguen válidas y el redirect por rol las lleva al destino correcto (edge case de sesiones del flujo anterior). El refresco de estado entre Carga → Consulta (FR-011) se logra invalidando la query key `["portal", "compliance"]` de TanStack Query tras upload/submit exitoso, patrón ya usado en el portal actual.

**Rationale**: Cero migraciones, cero cambios de sesión; reutiliza la invalidación de caché existente.

**Alternatives considered**: Forzar logout global al desplegar — innecesario; el comportamiento por rol ya es correcto.
