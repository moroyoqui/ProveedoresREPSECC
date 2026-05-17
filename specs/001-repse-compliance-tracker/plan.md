# Implementation Plan: Bóveda de Cumplimiento REPSE (Core)

**Branch**: `001-repse-compliance-tracker` | **Date**: 2026-05-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from [./spec.md](./spec.md)

**Note**: This file was authored by `/speckit-plan`. The companion artifacts ([research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)) are produced by the same command.

## Summary

Construir el núcleo del SaaS REPSE: una bóveda multi-tenant donde un cliente contratante registra a sus proveedores (cada uno asociado a un **Tipo de Proveedor** que define los documentos exigidos y su periodicidad efectiva), asocia documentos de cumplimiento (PDF/imágenes) contra el catálogo del tenant, calcula automáticamente el estado de cada documento (vigente / por vencer / vencido / faltante) y muestra un tablero por proveedor. Stack: **FastAPI + SQLAlchemy + MySQL** para el backend, **React + Tailwind** para el frontend, **OAuth/OIDC** (Google + Microsoft) para autenticación, **almacenamiento en disco local** para archivos, **Tesseract local** para OCR best-effort, **despliegue on-prem** con Docker Compose. Multi-tenant dentro de una sola instancia, aislado por `organization_id` en la capa de datos.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.4 (frontend)

**Primary Dependencies**:
- **Backend**: FastAPI ≥0.110, SQLAlchemy 2.x (async/sync mixed), Alembic, Pydantic v2, Authlib (OIDC), python-multipart (uploads), pytesseract + pdf2image (OCR), structlog, slowapi (rate limiting), passlib (futuras credenciales locales si se requieren), uvicorn (ASGI).
- **Frontend**: React 18, Vite, Tailwind CSS, Tanstack Query, React Router, react-hook-form + Zod, Headless UI/Radix Primitives, Lucide Icons.
- **Infra**: Caddy (reverse proxy + TLS automático), Docker Compose, GlitchTip (self-hosted error tracking, opcional).

**Storage**:
- **Base de datos**: MySQL 8.0 (utf8mb4_0900_ai_ci) gestionada con SQLAlchemy + Alembic.
- **Archivos**: disco local del servidor, organizado en `var/uploads/<tenant_id>/<supplier_id>/<doc_id>/<version>.<ext>` con permisos 0640. Servidos exclusivamente por endpoints autenticados que emiten un token de descarga de corta vida.

**Testing**:
- **Backend**: pytest + pytest-asyncio + httpx (cliente de tests), factory_boy + faker (fixtures), testcontainers-python para MySQL en CI/local.
- **Frontend**: Vitest + React Testing Library + MSW (mocks de API).
- **E2E**: Playwright (smoke tests por historia de usuario).

**Target Platform**: Linux x86_64 / arm64. Despliegue on-prem mediante Docker Compose (servicios: `app`, `worker`, `mysql`, `caddy`, opcionalmente `glitchtip`). Sin dependencia de servicios cloud.

**Project Type**: Web app (frontend + backend separados en monorepo).

**Performance Goals**:
- SC-001: registrar primer proveedor + cargar primer documento en <5 min para nuevo usuario.
- SC-003: 95% de acciones principales <2 s percibidas con tenant de 500 proveedores y 50 000 documentos.
- p95 de queries críticas (listado de proveedores, detalle, cálculo de estado) <300 ms con índices apropiados.

**Constraints**:
- **On-prem sin nube**: cero dependencias a servicios SaaS externos para correr el producto (Google/Microsoft OAuth son OIDC públicos, no costos operativos).
- **Multi-tenant en una sola instancia**: aislamiento garantizado por `organization_id` propagado desde la sesión OAuth, **forzado** en cada query a nivel ORM (mixin obligatorio + chequeo en CI).
- **Sin pérdida de datos**: backups diarios de MySQL + carpeta `var/uploads/` con `mysqldump` + `tar` a un volumen separado, restauración probada al menos cada trimestre.
- **OCR best-effort**: Tesseract puede fallar; nunca debe bloquear la carga del documento.

**Scale/Scope**:
- Target inicial (v1): ~20 organizaciones × ~200 proveedores × ~50 docs/año = ~200 000 documentos en disco después de 1 año.
- Target 5 años: ~100 organizaciones × ~500 proveedores × ~250 docs/año (5 años de histórico) = ~62 M filas en `documents`. Acotable con archivado a tablas particionadas si crece.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Se evalúa cada principio de [constitution.md](../../.specify/memory/constitution.md):

| Principio | Estado | Justificación / Cómo se cumple |
|-----------|--------|-------------------------------|
| **I. Secure by Default** | ✅ Pass | Caddy termina TLS automático en cualquier dominio no `localhost`. OAuth/OIDC delega contraseñas a proveedores corporativos (no hay credenciales locales en v1). Pydantic valida toda entrada. Archivos NUNCA expuestos por URL pública (FR-019). slowapi limita auth y endpoints públicos. **Desviación menor del spec**: FR-002 mencionaba "correo + contraseña hasheada con algoritmo moderno"; el plan reemplaza por OAuth/OIDC porque elimina por completo el manejo de contraseñas locales — más seguro y alineado al principio. Ver [Complexity Tracking](#complexity-tracking). |
| **II. Multi-Tenant Data Isolation** | ✅ Pass | Cada tabla con datos de cliente lleva `organization_id` NOT NULL + índice. Mixin `TenantOwned` en SQLAlchemy + dependencia `current_tenant` en FastAPI que **inyecta el filtro** en cada consulta. Test E2E negativo (Org A intenta leer recurso de Org B → 404, no 403) bloquea merge. |
| **III. Test-First for Critical Paths** | ✅ Pass | Auth, autorización, aislamiento tenant y cálculo de estado de documento se cubren con tests antes del merge. CI ejecuta `pytest` + `vitest` en cada PR. |
| **IV. Observability** | ✅ Pass | structlog emite JSON con `request_id`, `tenant_id`, `user_id` por request. Errores no controlados van a GlitchTip self-hosted (opcional, configurable). Métricas básicas (request rate, latency, error rate) expuestas en `/metrics` (Prometheus text format). Sin contraseñas, tokens ni PII innecesaria en logs (asserción en tests). |
| **V. Simplicity & YAGNI** | ✅ Pass | Una sola instancia, un solo binario backend, una sola DB. Sin colas externas, sin Redis, sin orquestadores hasta que el dolor lo justifique. OCR corre síncrono dentro del request o como BackgroundTask de FastAPI; Celery solo si la carga lo amerita. |

**Security & Compliance Requirements del documento de constitución**:

- Dependency scanning: `pip-audit` + `npm audit --omit=dev` en CI; high/critical bloquean merge. ✅
- Backups diarios automatizados (mysqldump + tar de uploads), restore probado por trimestre. ✅
- Mínima recolección de PII; eliminación al vencer el plazo de gracia (FR-015b). ✅
- TLS para integraciones externas (OAuth → siempre HTTPS). ✅
- Rate limiting en autenticación y endpoints públicos. ✅

**Resultado del Constitution Check**: PASS (con desviación menor en FR-002 documentada en Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/001-repse-compliance-tracker/
├── spec.md                # Especificación de producto
├── plan.md                # Este archivo
├── research.md            # Phase 0: decisiones técnicas + alternativas
├── data-model.md          # Phase 1: entidades, relaciones, índices, migrations
├── quickstart.md          # Phase 1: cómo correr el proyecto localmente
├── contracts/             # Phase 1: contratos de API (OpenAPI por dominio)
│   ├── auth.md
│   ├── organizations.md
│   ├── suppliers.md
│   ├── supplier-types.md
│   ├── document-types.md
│   ├── documents.md
│   └── audit.md
├── checklists/
│   └── requirements.md
└── tasks.md               # Phase 2 (NO creado aquí; viene en /speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                      # Poetry o uv; lockfile commiteado
├── alembic.ini
├── src/
│   └── repse/
│       ├── __init__.py
│       ├── main.py                     # FastAPI app, lifespan, middleware
│       ├── config.py                   # Settings (Pydantic BaseSettings)
│       ├── logging.py                  # structlog setup
│       ├── db/
│       │   ├── session.py              # SQLAlchemy engine + session factory
│       │   ├── base.py                 # DeclarativeBase + naming convention
│       │   └── tenant_filter.py        # TenantOwned mixin + event listeners
│       ├── auth/
│       │   ├── oidc.py                 # Authlib OIDC clients (Google, Microsoft)
│       │   ├── dependencies.py         # current_user, current_tenant, require_role
│       │   └── routes.py
│       ├── organizations/
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── service.py
│       │   └── routes.py
│       ├── suppliers/
│       │   └── ... (idem)
│       ├── supplier_types/
│       │   ├── models.py                 # SupplierType + SupplierTypeDocumentRequirement
│       │   ├── schemas.py
│       │   ├── service.py                # CRUD + recálculo de cumplimiento al editar requisitos
│       │   ├── templates.py              # Catálogo canónico de plantillas por industria
│       │   ├── provisioning.py           # bootstrap "Sin clasificar" al crear Organization
│       │   └── routes.py
│       ├── document_types/
│       │   └── ... (idem)
│       ├── documents/
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── service.py
│       │   ├── routes.py
│       │   ├── storage.py              # Disk-backed FileStore (signed download tokens)
│       │   ├── ocr.py                  # Tesseract wrapper (best-effort)
│       │   └── expiration.py           # Cálculo por periodicidad (mensual/bimestral SAT/anual)
│       ├── audit/
│       │   └── ... (modelo inmutable)
│       └── catalog/
│           └── canonical.py            # Catálogo canónico precargado (seed)
├── tests/
│   ├── conftest.py                     # MySQL testcontainer, factories
│   ├── unit/
│   ├── integration/                    # incluye casos negativos multi-tenant
│   └── e2e/                            # Playwright invocado desde aquí (smoke)
└── migrations/                         # Alembic
    └── versions/

frontend/
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── src/
│   ├── main.tsx
│   ├── app/
│   │   ├── router.tsx
│   │   ├── providers.tsx               # QueryClient, AuthProvider, ThemeProvider
│   │   └── layout.tsx
│   ├── pages/
│   │   ├── auth/
│   │   ├── dashboard/                  # (alcance del spec 005 cuando se construya)
│   │   ├── suppliers/
│   │   │   ├── list.tsx
│   │   │   ├── detail.tsx
│   │   │   └── new.tsx
│   │   └── documents/
│   │       └── upload.tsx
│   ├── components/
│   │   ├── ui/                         # primitives (Button, Card, Badge, Table)
│   │   ├── suppliers/
│   │   └── documents/
│   ├── lib/
│   │   ├── api.ts                      # Fetch wrapper con auth headers
│   │   └── status.ts                   # Compliance status helpers (cliente)
│   └── styles/
│       └── globals.css                 # Tailwind base + tokens de color del spec FR-016
└── tests/
    ├── unit/
    └── e2e/                            # Playwright tests para US1 y US2

ops/
├── docker-compose.yml                  # app, mysql, caddy (+ glitchtip opcional)
├── Dockerfile.app
├── Dockerfile.frontend
├── Caddyfile
├── .env.example                        # variables documentadas
└── scripts/
    ├── backup.sh                       # mysqldump + tar uploads
    └── restore.sh
```

**Structure Decision**: Monorepo con `backend/` (FastAPI + SQLAlchemy + Alembic) y `frontend/` (React + Vite + Tailwind) como hermanos, más `ops/` con la receta de Docker Compose para el despliegue on-prem. La frontera de tenant se materializa en el backend mediante mixin SQL + dependencia FastAPI; el frontend nunca decide a qué tenant pertenece un recurso. Cada dominio (`organizations`, `suppliers`, `document_types`, `documents`, `audit`) es un módulo cohesivo con `models.py`, `schemas.py`, `service.py`, `routes.py` (sin sobre-ingeniería: no introducimos "interfaces" ni capas extra hasta que duela).

## Complexity Tracking

| Decisión | Por qué se aparta del default | Alternativa simple rechazada porque |
|----------|------------------------------|-------------------------------------|
| **OAuth/OIDC en lugar de email+password** (desviación de spec FR-002) | El usuario eligió OAuth en el plan técnico. Elimina por completo el manejo de credenciales locales (no hay contraseñas que hashear, restablecer ni filtrar). Google y Microsoft son los IDPs más comunes en el mercado B2B mexicano. | Email + password local (lo que decía el spec) implicaba implementar reset de contraseña, flujos de bloqueo, expiración y rotación. Más superficie de ataque, más código de seguridad que el equipo debe mantener. Se actualizará el spec en `/speckit-clarify` si el equipo quiere mantener simétrico el documento; mientras tanto se respeta la decisión del plan y se documenta aquí. |
| **MySQL en lugar de PostgreSQL** | Decisión del usuario. MySQL 8.0 es maduro, multi-tenant-safe y conocido por equipos en LATAM; cumple con todos los requisitos del spec. | PostgreSQL ofrece tipos avanzados (JSONB, partial indexes ricos). En este dominio MySQL 8 cubre todo (JSON nativo, CTEs, particionado). No hay funcionalidad bloqueante. |
| **Disco local en lugar de S3-compatible** | Despliegue on-prem sin nube por requisito explícito. | Object storage (S3/MinIO) introduciría un servicio extra que opera localmente solo con MinIO; mismo modelo mental, más complejidad operativa. Si en el futuro se ofrece despliegue cloud, se introduce `FileStore` con backend pluggable. |
| **OCR síncrono en el request inicialmente** | YAGNI: pdf2image + tesseract sobre PDFs típicos (≤5 MB) responde en <3 s. Comenzar simple. | Cola de jobs (Celery + Redis) o BackgroundTasks desde el día 1 agrega 2 servicios y errores asíncronos sin beneficio en v1. Cuando un OCR tarde >5 s, se mueve a `BackgroundTasks` (FastAPI) y posteriormente a worker dedicado si la métrica lo pide. |

---

**Phase 0 (research)**: ver [research.md](./research.md).

**Phase 1 (design)**: ver [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).
