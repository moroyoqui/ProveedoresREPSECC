# Quickstart: Alertas y Recordatorios de Cumplimiento

Esta guía asume que la bóveda del [spec 001](../001-repse-compliance-tracker/quickstart.md) ya corre localmente. Aquí se agrega un servidor SMTP local para validar correos y se documenta cómo probar el flujo end-to-end de alertas.

## Prerrequisitos adicionales

- Stack del 001 corriendo (`docker compose up`).
- **Servidor SMTP de pruebas**: usa **MailHog** o **Mailpit** en Docker — capturan todos los correos en una UI web sin enviarlos al mundo real.

## Variables de entorno nuevas

Añade a tu `.env`:

```ini
# Scheduler
ALERTS_SCHEDULER_ENABLED=true

# SMTP (para desarrollo apuntamos a Mailpit local)
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_USE_STARTTLS=false       # mailpit no soporta TLS por defecto
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=notificaciones@local.test
SMTP_FROM_NAME=Cumplimiento REPSE
SMTP_TIMEOUT_SECONDS=10
```

Para producción on-prem (Exchange / SES / Postmark): cambia `SMTP_HOST/PORT/USERNAME/PASSWORD` y enciende `SMTP_USE_STARTTLS=true`.

## Docker Compose: agregar Mailpit

Añade un servicio en `ops/docker-compose.yml`:

```yaml
  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "8025:8025"   # UI web
      - "1025:1025"   # SMTP
    restart: unless-stopped
```

UI: <http://localhost:8025>.

## Aplicar migraciones de 002

```bash
docker compose exec app alembic upgrade head
# Crea las 4 tablas nuevas: alert_config, supplier_alert_recipient_overrides,
# alert_silences, notifications. Y siembra AlertConfig por defecto en
# organizaciones existentes (0011_seed_alert_config_existing_orgs).
```

## Smoke test E2E

### 1. Configurar alertas

```bash
curl -X PATCH https://localhost/api/v1/alerts/config \
  -b cookies.txt -H "Content-Type: application/json" \
  -d '{
    "expiring_lead_time_days": 15,
    "default_recipient_emails": ["compliance@local.test"],
    "daily_run_at": "08:00:00"
  }'
```

### 2. Sembrar un documento que vencerá en 10 días

Desde un script Python en el contenedor `app`:

```python
docker compose exec app python -m repse.scripts.seed_doc_expiring_in_days \
  --supplier-id 12 --document-type-slug opinion-sat --days-until-due 10
```

(Este script vive en `backend/src/repse/scripts/` y es solo para dev/test; se excluye del build productivo.)

### 3. Disparar el barrido manualmente

```bash
curl -X POST https://localhost/api/v1/alerts/trigger-now -b cookies.txt
# 202 Accepted, scheduled_at: ...
```

### 4. Validar resultados

- **Mailpit UI** (<http://localhost:8025>): debería aparecer 1 correo a `compliance@local.test` con el tema "Documentos por vencer — Servicios Industriales del Norte".
- **In-app**:
  ```bash
  curl https://localhost/api/v1/notifications/unread-count -b cookies.txt
  # { "unread_count": 1, ... }
  ```

### 5. Validar idempotencia

```bash
curl -X POST https://localhost/api/v1/alerts/trigger-now -b cookies.txt
# 202 Accepted (segunda invocación)
# Tras esperar el tick: no aparece un segundo correo en Mailpit ni una segunda
# notificación in-app. La constraint unique de notifications lo bloqueó.
```

### 6. Validar silenciamiento

```bash
curl -X POST https://localhost/api/v1/documents/4521/silence \
  -b cookies.txt -H "Content-Type: application/json" \
  -d '{ "reason": "En revisión hasta fin de mes" }'

# Al día siguiente (sembrado avanzando reloj con freezegun), el documento
# NO genera nueva notificación de "vencido" hasta que se levante el silencio.
```

## Operación

| Tarea | Comando |
|-------|---------|
| Ver el último run | `curl /api/v1/alerts/config \| jq '.last_run_at,.last_run_status'` |
| Reenviar fallidas manualmente | `docker compose exec app python -m repse.alerts.cli retry-failed --org 7` |
| Ver métricas | `curl http://localhost:9100/metrics \| grep notifications_` |
| Deshabilitar alertas para un tenant | `PATCH /api/v1/alerts/config { "enabled": false }` |
| Cambiar zona horaria | `PATCH /api/v1/organization { "timezone": "America/Bogota" }` (afecta `daily_run_at`) |

## Tests automatizados

```bash
# Backend
docker compose exec app pytest tests/integration/test_alerts_scheduler.py -v
docker compose exec app pytest tests/integration/test_alerts_idempotency.py -v
docker compose exec app pytest tests/integration/test_alerts_multitenant.py -v
docker compose exec app pytest tests/contract/test_alerts_contracts.py -v

# Frontend
docker compose exec frontend pnpm vitest run src/components/notifications/
docker compose exec frontend pnpm playwright test tests/e2e/us1_alert_received.spec.ts
```

## Recuperación de incidentes

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| Correos no llegan, métrica `notifications_sent_total{result="failed"}` aumenta | SMTP mal configurado | Verifica `SMTP_*` env vars, prueba `docker compose exec app python -m repse.alerts.cli test-smtp <email>` |
| Notificaciones in-app sí, pero correos no | Lo mismo (in-app no depende de SMTP) | Igual al anterior |
| Doble correo por documento el mismo día | Bug en la constraint unique o índice ausente | `SHOW INDEX FROM notifications` y verifica que `uq_notifications_dedup` exista |
| Scheduler no corre | `ALERTS_SCHEDULER_ENABLED=false` o `enabled=false` en AlertConfig | Revisa env y `GET /api/v1/alerts/config` |
| Hora equivocada | `organizations.timezone` inválida | `PATCH /api/v1/organization { "timezone": "America/Mexico_City" }` |

## Próximos pasos en el flujo Spec Kit

- `/speckit-tasks` para descomponer este plan en tareas accionables.
- `/speckit-implement` para ejecutar.
