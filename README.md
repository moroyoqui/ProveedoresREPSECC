# ProveedoresREPSECC

SaaS para gestión del cumplimiento REPSE de proveedores bajo el Art. 15 de la Ley Federal del Trabajo.

## Monorepo

```
backend/    FastAPI + SQLAlchemy + MySQL
frontend/   Vite + React 18 + TypeScript + Tailwind
ops/        Docker Compose + Caddy + scripts on-prem
specs/      Spec Kit specifications, plans, tasks
```

## Quickstart

Ver [specs/001-repse-compliance-tracker/quickstart.md](specs/001-repse-compliance-tracker/quickstart.md) para arrancar localmente con Docker Compose.

```bash
cp ops/.env.example .env
docker compose -f ops/docker-compose.yml up -d
docker compose -f ops/docker-compose.yml exec app alembic upgrade head
open https://localhost
```

## Stack

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 |
| Auth | Email + contraseña (hash Argon2) con cookie de sesión firmada |
| DB | MySQL 8.0 |
| Storage | Disco local con tokens JWS firmados |
| OCR | Tesseract local (pytesseract + pdf2image) |
| Frontend | React 18, Vite, TypeScript, Tailwind, Tanstack Query |
| Infra | Docker Compose, Caddy (reverse proxy + TLS automático) |

Decisiones y rationale completos en [specs/001-repse-compliance-tracker/](specs/001-repse-compliance-tracker/).

## Constitución del proyecto

Las cinco principios no negociables viven en [.specify/memory/constitution.md](.specify/memory/constitution.md):

1. Secure by Default
2. Multi-Tenant Data Isolation
3. Test-First for Critical Paths
4. Observability
5. Simplicity & YAGNI (con [Complexity Tracking](specs/001-repse-compliance-tracker/plan.md#complexity-tracking) cuando aplica)
