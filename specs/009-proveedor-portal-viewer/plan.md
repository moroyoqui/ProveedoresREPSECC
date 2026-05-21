# Implementation Plan: Portal del Proveedor — Visor de Documentación

**Branch**: `009-proveedor-portal-viewer` | **Date**: 2026-05-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-proveedor-portal-viewer/spec.md`

## Summary

Agregar un rol `supplier` al sistema de usuarios y un portal exclusivo para proveedores donde pueden consultar el estado de cumplimiento de su documentación, cargar archivos en celdas con estado `missing`/`expired`/`pending`, y enviar paquetes a revisión de contabilidad con un solo clic. El portal reutiliza la lógica de negocio existente (`get_annual_compliance`, `upload_document`, `ComplianceGridOut`) y agrega una nueva tabla `portal_submissions` para el flujo de envío a validación. La interfaz de contabilidad para aprobar/rechazar solicitudes queda fuera del alcance de esta feature.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5.x + React 18 (frontend)

**Primary Dependencies**: FastAPI + SQLAlchemy 2.x (backend); React 18 + Vite + TanStack Query v5 + Tailwind CSS (frontend); itsdangerous (sesión cookie firmada); Authlib (OIDC)

**Storage**: MySQL 8 (base de datos relacional) + disco local (archivos de documentos)

**Testing**: pytest (backend) — tests de auth, aislamiento de tenant, upload y submit requeridos por Constitución Principio III

**Target Platform**: Linux server on-prem; Docker Compose con Caddy reverse proxy

**Project Type**: web-service (FastAPI) + web-application (React SPA)

**Performance Goals**: `GET /api/v1/portal/compliance` < 500 ms p95 con 12 meses de histórico (SC-002)

**Constraints**: Sesión cookie HttpOnly/Secure/SameSite=Lax; `supplier_id` NUNCA aceptado como parámetro externo; aislamiento de tenant obligatorio en todas las queries de `portal_submissions`

**Scale/Scope**: ~10–50 proveedores por organización en v1; un usuario proveedor vinculado a exactamente una empresa

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Evidencia |
|---|---|---|
| **I. Secure by Default** | ✅ PASS | Todos los endpoints del portal usan `require_role(Role.SUPPLIER)`; `supplier_id` extraído exclusivamente del payload de sesión firmado (nunca de URL/body); validación de estado de celda antes de permitir upload o submit |
| **II. Multi-Tenant Data Isolation** | ✅ PASS | `organization_id` incluido en todas las queries de `portal_submissions`; test T006 cubre el caso negativo (supplier A no puede ver datos de supplier B ni de otra organización) |
| **III. Test-First for Critical Paths** | ✅ PASS | T005 (auth), T006 (isolation), T030 (upload) y T035 (submit) son tests obligatorios escritos antes de la implementación correspondiente |
| **IV. Simplicity / YAGNI** | ✅ PASS | Reutiliza `get_annual_compliance()`, `upload_document()` y `ComplianceGridOut` sin duplicar lógica; relación 1:1 usuario↔proveedor con FK directo en `users.supplier_id` (sin tabla de enlace); sin constraint UNIQUE en BD — la unicidad `status='pending'` por celda se valida en capa de aplicación |

**Post-design re-check**: Ninguna violación identificada. La adición de `portal_submissions` como tabla separada (no extender `ComplianceCellValidation`) es la solución más simple que soporta el flujo de múltiples rondas de envío/rechazo con historial.

## Project Structure

### Documentation (this feature)

```text
specs/009-proveedor-portal-viewer/
├── plan.md              # Este archivo (/speckit-plan command output)
├── spec.md              # Especificación de feature con US1–US6
├── research.md          # Phase 0 — 10 decisiones de diseño documentadas
├── data-model.md        # Phase 1 — esquema de BD, máquina de estados, validaciones
├── contracts/
│   └── portal-compliance.md  # Contratos de los 5 endpoints del portal
└── tasks.md             # Phase 2 — 43 tareas en 9 fases (generado por /speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/repse/
│   ├── portal/
│   │   ├── __init__.py
│   │   ├── models.py          # PortalSubmission, SubmissionStatus, PreSubmissionStatus
│   │   ├── routes.py          # 5 endpoints: GET /compliance, GET /history/{id},
│   │   │                      #   POST /upload, POST /submit/{id}, GET /submission/{id}
│   │   └── schemas.py         # SubmissionOut, UploadOut, SubmitRequest, SubmissionDetail
│   ├── users/
│   │   ├── models.py          # Role.SUPPLIER agregado; users.supplier_id FK
│   │   ├── schemas.py         # supplier_id en UserOut/UserCreate/UserPatch + validador
│   │   └── routes.py          # Validación de supplier_id al crear/actualizar usuario proveedor
│   ├── auth/
│   │   ├── session.py         # SessionPayload.supplier_id (backward-compatible)
│   │   ├── dependencies.py    # CurrentUser.supplier_id propagado desde sesión
│   │   └── routes.py          # login/callback incluyen supplier_id en SessionPayload
│   └── compliance/
│       └── service.py         # get_annual_compliance() + query a portal_submissions (Decision 10)
├── alembic/versions/
│   ├── 0005_add_supplier_role_and_user_supplier_link.py
│   └── 0006_add_portal_submissions.py
└── tests/
    ├── test_portal_auth.py       # 401/403/409 + camino feliz con rol supplier
    ├── test_portal_isolation.py  # Aislamiento tenant: supplier A ≠ supplier B; org X ≠ org Y
    ├── test_portal_upload.py     # Tests negativos upload + camino feliz 201
    └── test_portal_submit.py     # Tests negativos submit + camino feliz 201 + GET submission

frontend/
└── src/
    ├── lib/
    │   ├── auth.tsx               # Role incluye "supplier"; AuthUser.supplierId
    │   └── api/
    │       ├── index.ts           # Role incluye "supplier"; UserItem.supplier_id
    │       └── portal.ts          # portalApi: getCompliance, getDocumentHistory,
    │                              #   upload, submit, getSubmission
    ├── pages/portal/
    │   └── index.tsx              # PortalPage: grid + alertas + PendingSubmitSection
    ├── components/portal/
    │   ├── UploadPortalDialog.tsx      # Diálogo multi-archivo con feedback individual
    │   ├── SubmitValidationButton.tsx  # CTA destacado; confirm dialog; inhabilitar tras envío
    │   └── RejectionReasonBanner.tsx   # Banner de rechazo con motivo de contabilidad
    └── app/
        └── router.tsx             # /portal route; redirect por rol (supplier → /portal)
```

**Structure Decision**: Opción 2 (web application). El backend FastAPI mantiene su estructura de módulos por dominio; el nuevo paquete `repse/portal/` sigue el mismo patrón (models + routes + schemas). El frontend agrega `pages/portal/` y `components/portal/` sin modificar la estructura existente de componentes administrativos.

## Complexity Tracking

> **No hay violaciones de la Constitución** — este cuadro queda vacío.

| Violación | Por qué se necesita | Alternativa más simple descartada porque |
|---|---|---|
| — | — | — |
