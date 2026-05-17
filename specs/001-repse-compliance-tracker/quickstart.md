# Quickstart: Bóveda de Cumplimiento REPSE (Core)

Guía para correr el proyecto localmente y para desplegarlo on-prem con Docker Compose. Aplica al backend FastAPI, el frontend React y la infra mínima (MySQL + Caddy).

## Prerrequisitos

- **macOS / Linux / Windows con WSL2**.
- **Docker Desktop** ≥ 4.30 o `docker` + `docker compose` v2.
- **Python** 3.12 (solo si quieres correr el backend sin Docker para desarrollo rápido).
- **Node.js** 20 LTS + `pnpm` 9 (solo para correr el frontend fuera de Docker).
- Acceso a las credenciales OIDC: Google Cloud Console (Client ID + Secret con redirect `https://<host>/api/v1/auth/callback/google`) y Microsoft Entra (App Registration con redirect `https://<host>/api/v1/auth/callback/microsoft`).

## Estructura mínima de variables de entorno

`.env` en raíz (copiar de `ops/.env.example`):

```ini
# App
APP_ENV=local           # local | staging | prod
APP_SECRET=<32+ bytes>  # firma sesiones y tokens de descarga
APP_BASE_URL=http://localhost:8080
UPLOAD_ROOT=./var/uploads

# DB
DB_HOST=mysql
DB_PORT=3306
DB_NAME=repse
DB_USER=repse
DB_PASS=<password>

# OIDC
OIDC_GOOGLE_CLIENT_ID=...
OIDC_GOOGLE_CLIENT_SECRET=...
OIDC_MICROSOFT_CLIENT_ID=...
OIDC_MICROSOFT_CLIENT_SECRET=...
OIDC_MICROSOFT_TENANT=common   # 'common' acepta cualquier Entra; 'consumers' solo Microsoft personal

# Tesseract
TESSERACT_LANG=spa+eng

# Observabilidad (opcional)
SENTRY_DSN=
PROMETHEUS_ENABLED=true
```

## Caminos de uso

### A. Desarrollo local con Docker (recomendado)

```bash
# Levanta MySQL, backend, frontend y Caddy en modo dev
docker compose -f ops/docker-compose.yml --env-file .env up -d

# Aplica migraciones y siembra catálogo canónico
docker compose -f ops/docker-compose.yml run --rm app alembic upgrade head

# Abre la app
open https://localhost   # Caddy emite cert local con `tls internal`
```

### B. Desarrollo local sin Docker (solo backend)

```bash
# MySQL en Docker, app en host
docker compose -f ops/docker-compose.yml up -d mysql

# Backend
cd backend
uv sync                  # o poetry install
uv run alembic upgrade head
uv run uvicorn repse.main:app --reload --port 8000
```

```bash
# Frontend
cd frontend
pnpm install
pnpm dev                 # corre en http://localhost:5173 con proxy a /api → :8000
```

### C. Despliegue on-prem (single server)

```bash
# En el servidor on-prem
git clone <repo> /opt/repse
cd /opt/repse
cp ops/.env.example .env
$EDITOR .env             # llena APP_BASE_URL, OIDC*, DB_PASS, APP_SECRET

# Levanta el stack productivo
docker compose -f ops/docker-compose.prod.yml --env-file .env up -d
docker compose -f ops/docker-compose.prod.yml --env-file .env exec app alembic upgrade head

# Backups
sudo systemctl enable --now repse-backup.timer   # diario 02:00
```

## Smoke test (US1 + US2)

Verifica que la implementación cubre las dos historias de usuario del spec.

```bash
# 1. Login OAuth (manual, en navegador)
open https://localhost/api/v1/auth/login/google

# 2. Crea un proveedor por API
curl -X POST https://localhost/api/v1/suppliers \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "legal_name": "Servicios Industriales del Norte SA de CV",
    "rfc": "SIN9001022Y3",
    "contact_email": "juanp@sin.mx"
  }'

# 3. Sube una opinión SAT contra ese proveedor
curl -X POST https://localhost/api/v1/suppliers/12/documents \
  -b cookies.txt \
  -F "file=@./opinion-sat-abril.pdf" \
  -F "document_type_id=1" \
  -F "coverage_period_start=2026-04-01"

# 4. Verifica que el estado se calculó
curl https://localhost/api/v1/suppliers/12 -b cookies.txt | jq '.documents_by_type[0]'
```

Los tests E2E de Playwright (`backend/tests/e2e/`) ejecutan estos mismos pasos sin intervención manual usando un mock de proveedor OIDC (`oauthlib.oauth2.MockProvider`).

## Operación

| Tarea | Comando |
|-------|---------|
| Aplicar migraciones | `docker compose exec app alembic upgrade head` |
| Crear migración nueva | `docker compose exec app alembic revision -m "describe change"` |
| Tomar backup manual | `ops/scripts/backup.sh /var/backups/repse` |
| Restaurar de backup | `ops/scripts/restore.sh /var/backups/repse/<fecha>` |
| Revisar métricas | `curl http://localhost:9100/metrics` (sólo accesible desde la red interna) |
| Ver logs en vivo | `docker compose logs -f app` |
| Probar OCR de un PDF | `docker compose exec app python -m repse.documents.ocr.cli ./sample.pdf` |

## Recuperación de incidentes

1. **MySQL corrupto**: detén `app`, restaura el backup más reciente con `ops/scripts/restore.sh`, sube `app` y verifica con el smoke test.
2. **Carpeta `uploads` inaccesible**: el endpoint `/api/v1/files/{token}` responde `500 storage_unavailable`. Restaura de `var/backups/uploads-YYYYMMDD.tar.gz`.
3. **Sesiones inválidas tras rotar `APP_SECRET`**: todos los usuarios deben volver a iniciar sesión; no hay invalidación parcial.
4. **OCR atorado**: matar el contenedor `app` y reiniciar; los documentos en `ocr_status='pending'` se recalculan con `python -m repse.documents.ocr.recalc`.

## Próximos pasos en el flujo Spec Kit

- `/speckit-tasks` para generar la lista accionable de tareas a partir de este plan.
- `/speckit-implement` para ejecutar el plan completo en automático (después de tasks).
