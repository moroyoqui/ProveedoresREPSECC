# Data Model — 013 Portal Upload Separation

**Date**: 2026-06-11 · **Spec**: [spec.md](spec.md) · **Research**: [research.md](research.md)

## Resumen

**Esta feature no introduce tablas, columnas ni migraciones.** Reutiliza íntegro el modelo de 009 (`users.supplier_id`, `portal_submissions`, `documents`, `compliance_cell_validations`). La separación es de presentación (rutas/pantallas), de entrada (audiencia de login) y de organización de servicios (routers read/write).

## Cambios en contratos de datos (no persistidos)

### `LoginIn` (request de `POST /api/v1/auth/login`)

| Campo | Tipo | Cambio |
|---|---|---|
| `email` | EmailStr | sin cambio |
| `password` | str | sin cambio |
| `audience` | `"backoffice" \| "portal"` | **nuevo**, opcional, default `"backoffice"` (retrocompatible) |

**Regla de validación** (tras `verify_password` exitoso):

- `audience == "portal"` y `role != supplier` → error genérico `invalid_credentials` (mismo que credenciales inválidas).
- `audience == "backoffice"` y `role == supplier` → error genérico `invalid_credentials`.
- Nunca se emite un código distinto que permita distinguir "credencial inválida" de "puerta equivocada" (FR-013).

### `SessionPayload`

Sin cambios. El rol en la sesión sigue siendo la única fuente de verdad para autorización; las sesiones emitidas antes de esta feature permanecen válidas.

## Clasificación de operaciones del portal (FR-009)

| Endpoint | Método | Grupo | Escrituras a BD |
|---|---|---|---|
| `/api/v1/portal/compliance` | GET | read (`routes_read.py`) | ninguna |
| `/api/v1/portal/history/{document_type_id}` | GET | read | ninguna |
| `/api/v1/portal/submission/{document_type_id}` | GET | read | ninguna |
| `/api/v1/portal/upload` | POST | write (`routes_write.py`) | `documents` (vía `upload_document`) |
| `/api/v1/portal/submit/{document_type_id}` | POST | write | `portal_submissions` |

Invariante verificable por test: los handlers del grupo read no invocan `db.add`/`db.commit`/`db.delete` y solo registran métodos GET.

## Mapa de rutas frontend (estado objetivo)

| Ruta | Audiencia | Layout | Contenido |
|---|---|---|---|
| `/login` | back-office | — | login administrativo (email+password, OIDC); enlace estático al portal |
| `/portal/login` | proveedor | — | login del portal (email+password); enlace estático al acceso administrativo |
| `/portal` | proveedor | — | redirect → `/portal/consulta` (FR-006) |
| `/portal/consulta` | proveedor | `PortalShell` | grid de cumplimiento, alertas, historial, motivo de rechazo — solo lectura |
| `/portal/carga` | proveedor | `PortalShell` | celdas elegibles (`missing`/`expired`), diálogo multi-archivo, "Enviar a validar" |
| rutas administrativas existentes | back-office | `AppShell` | sin cambios; `AppShell` pierde la rama condicional supplier |

Guardas de ruta: las rutas `/portal/*` exigen rol `supplier` (guard nuevo `RequireSupplier`); las administrativas conservan `RequireNonSupplier`. Un admin que navega a `/portal/*` es redirigido a su área (edge case de la spec), y viceversa.

## Estados y transiciones

Sin cambios respecto a 009. La elegibilidad de carga (`missing`/`expired`, sin períodos futuros, bloqueo en `pending`/validada/`expiring_soon`) sigue implementada en `_check_upload_allowed` y `portal_submit`, que se mueven a `routes_write.py` sin modificación de lógica (FR-007).
