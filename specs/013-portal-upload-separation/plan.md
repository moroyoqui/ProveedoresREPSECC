# Implementation Plan: Separación de Pantallas de Carga y Consulta en el Portal del Proveedor

**Branch**: `013-portal-upload-separation` | **Date**: 2026-06-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/013-portal-upload-separation/spec.md`

## Summary

Separar por completo la experiencia del proveedor de la del back-office sobre lo ya implementado en 009: (1) login dedicado `/portal/login` con gating por audiencia en `POST /auth/login` (campo opcional `audience`, respuesta de mismatch idéntica a credenciales inválidas); (2) layout propio `PortalShell` con menú exclusivo y dos pantallas — `/portal/consulta` (solo lectura) y `/portal/carga` (upload + enviar a validar) — repartiendo los componentes existentes del portal; (3) segregación del router backend en `routes_read.py` (3 GET sin escrituras) y `routes_write.py` (2 POST) bajo las mismas URLs. Cero migraciones de BD, cero cambios de reglas de negocio.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5.x + React 18 (frontend)

**Primary Dependencies**: FastAPI + SQLAlchemy 2.x; React 18 + Vite + TanStack Query v5 + Tailwind CSS + react-router-dom; itsdangerous (cookie de sesión firmada); Authlib (OIDC, sin cambios)

**Storage**: MySQL 8 + disco local — **sin migraciones ni cambios de esquema en esta feature**

**Testing**: pytest (backend); tests de audiencia de login, solo-lectura del grupo read y 403 cruzados obligatorios por Constitución III

**Target Platform**: Linux server on-prem; Docker Compose con Caddy

**Project Type**: web-service (FastAPI) + web-application (React SPA)

**Performance Goals**: sin cambios respecto a 009 (`GET /api/v1/portal/compliance` < 500 ms p95); la separación no agrega round-trips nuevos al flujo del proveedor

**Constraints**: respuesta de login con audiencia equivocada indistinguible de credenciales inválidas (FR-013); URLs de los endpoints del portal sin cambios; `supplier_id` sigue saliendo solo de la sesión firmada; sesiones previas al despliegue permanecen válidas

**Scale/Scope**: 2 páginas nuevas + 1 layout + 1 página de login (frontend); split de 1 módulo de rutas + 1 campo en `LoginIn` (backend); ~10–50 proveedores por organización

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Evidencia |
|---|---|---|
| **I. Secure by Default** | ✅ PASS | Sin endpoints nuevos sin auth; gating de audiencia endurece el login sin filtrar validez de credenciales (Decision 3); `require_role` intacto en ambos grupos de rutas |
| **II. Multi-Tenant Data Isolation** | ✅ PASS | Cero queries nuevas; las existentes (ya scoped por `organization_id`/`supplier_id`) se mueven de archivo sin modificarse; suites de aislamiento de 009 deben seguir en verde |
| **III. Test-First for Critical Paths** | ✅ PASS | `test_auth_entry.py` (audiencia) y `test_portal_read_only.py` (solo lectura + 403 cruzados) se escriben antes que el código que validan; cambio en login es ruta crítica de auth |
| **IV. Simplicity / YAGNI** | ✅ PASS | Sin tablas, sin middleware nuevo, sin endpoint de login paralelo; OIDC sin tocar (Decision 4); URLs estables para no migrar clientes |

**Post-design re-check**: Sin violaciones. La única tentación de complejidad (prefijos de URL nuevos `/portal/consulta/*`) fue rechazada en Decision 5.

## Project Structure

### Documentation (this feature)

```text
specs/013-portal-upload-separation/
├── plan.md              # Este archivo
├── spec.md              # US1–US4, FR-001..FR-015
├── research.md          # Phase 0 — 7 decisiones
├── data-model.md        # Phase 1 — sin migraciones; contratos no persistidos y mapa de rutas
├── quickstart.md        # Phase 1 — verificación manual y tests
├── contracts/
│   └── auth-and-routes.md   # Contrato de login con audiencia + matriz de autorización + navegación
└── tasks.md             # Phase 2 (/speckit-tasks — pendiente)
```

### Source Code (repository root)

```text
backend/
├── src/repse/
│   ├── auth/
│   │   └── routes.py            # LoginIn.audience + regla de mismatch → invalid_credentials (routes.py:159-212)
│   ├── portal/
│   │   ├── routes_read.py       # NUEVO: GET /compliance, /history/{id}, /submission/{id} (movidos sin cambio de lógica)
│   │   ├── routes_write.py      # NUEVO: POST /upload, /submit/{id} + _check_upload_allowed (movidos)
│   │   └── routes.py            # ELIMINADO tras el split (main.py monta read+write bajo /api/v1/portal)
│   └── main.py                  # include_router de los dos routers del portal, mismo prefijo
└── tests/
    ├── test_auth_entry.py       # NUEVO: audiencia correcta/cruzada/byte-equivalencia del error
    └── test_portal_read_only.py # NUEVO: grupo read solo GET sin escrituras; supplier→admin 403 (SC-003/004)

frontend/
└── src/
    ├── app/router.tsx                   # /portal/login; /portal → redirect consulta; /portal/consulta|carga
    │                                    #   bajo PortalShell con guard RequireSupplier; AppShell solo back-office
    ├── components/layout/
    │   ├── AppShell.tsx                 # se elimina la rama condicional supplier (AppShell.tsx:71-84)
    │   └── PortalShell.tsx              # NUEVO: menú Consulta/Carga/cerrar sesión, identidad del portal
    ├── pages/auth/login.tsx             # agrega enlace estático "¿Eres proveedor? Entra por el portal"
    ├── pages/portal/
    │   ├── login.tsx                    # NUEVO: login del portal (email+password, audience:"portal")
    │   ├── consulta.tsx                 # NUEVO: grid + alertas + historial + RejectionReasonBanner (solo lectura)
    │   ├── carga.tsx                    # NUEVO: celdas elegibles + UploadPortalDialog + SubmitValidationButton;
    │   │                                #   lee ?type=&period= para preselección (FR-004)
    │   └── index.tsx                    # ELIMINADO tras repartir su contenido en consulta/carga
    └── components/portal/               # UploadPortalDialog, SubmitValidationButton, RejectionReasonBanner
                                         #   se reutilizan sin cambios de comportamiento
```

**Structure Decision**: Web application (backend FastAPI por dominios + SPA React). El paquete `repse/portal/` conserva su lugar; solo se divide su módulo de rutas por naturaleza read/write. En frontend, el portal gana su propio layout (`PortalShell`) y sus páginas viven en `pages/portal/` como hasta ahora.

## Complexity Tracking

> **No hay violaciones de la Constitución** — este cuadro queda vacío.

| Violación | Por qué se necesita | Alternativa más simple descartada porque |
|---|---|---|
| — | — | — |
