# Phase 0 Research: Alertas y Recordatorios de Cumplimiento

Resuelve los unknowns del [plan.md](./plan.md). Hereda del [research del 001](../001-repse-compliance-tracker/research.md) las decisiones de stack y solo trata lo nuevo: scheduler, correo, idempotencia, time zones y templating.

---

## 1. Scheduler diario (in-process vs externo)

**Decisión**: `APScheduler` en modo async dentro del proceso uvicorn de `app`. Se arranca/detiene en el lifespan de FastAPI.

**Rationale**:
- Volumen estimado (≤ ~25 000 docs/tenant, ~20 tenants) corre en <30 s en una sola máquina; no necesita worker dedicado.
- Operador on-prem **NO** debe instalar cron, systemd timers ni Redis: el binario `app` se autocontiene en su Docker.
- Si en el futuro hay multi-réplica de `app`, basta con elegir una réplica como "leader" (env `ALERTS_SCHEDULER_ENABLED=true`) — APScheduler ya soporta esto con jobstore en MySQL.

**Implementación**:
```python
# alerts/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=settings.db_url)},
    timezone="UTC",  # los jobs internamente computan tz por tenant
)

@app.on_event("startup")
async def _start():
    if settings.alerts_scheduler_enabled:
        scheduler.add_job(
            run_daily_alerts_for_all_tenants,
            "interval",
            minutes=5,  # tick frecuente; el job decide qué tenants ya corrieron HOY
            id="daily-alert-tick",
            replace_existing=True,
        )
        scheduler.start()
```

El tick cada 5 min permite respetar la hora configurada por tenant: cuando `now.in_tenant_tz() >= tenant.daily_run_at` y `last_run_at < hoy`, ejecuta el barrido para ese tenant.

**Alternativas**:
- **Celery + Beat + Redis**: 3 servicios extra. YAGNI para v1.
- **cron del host**: rompe el modelo Docker autocontenido; difícil de probar.
- **`asyncio.create_task` simple en un loop**: sin persistencia ni recuperación tras restart; APScheduler con SQLAlchemy jobstore mantiene el estado.

---

## 2. Transporte de correo

**Decisión**: cliente SMTP genérico con `aiosmtplib`. STARTTLS obligatorio cuando `SMTP_PORT != 25`; modo plaintext solo permitido para SMTP en localhost o red interna privada.

**Rationale**:
- On-prem heterogéneo: cada cliente trae su propio proveedor (SES, Postmark, SendGrid, Exchange corporativo, Postfix relay…).
- `aiosmtplib` es async (encaja con FastAPI), soporta STARTTLS, SSL directo, autenticación PLAIN/LOGIN.
- Cero acoplamiento a SDKs propietarios; cero vendor lock-in.

**Variables de entorno**:

```ini
SMTP_HOST=smtp.acme.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_USE_STARTTLS=true       # default true cuando PORT != 25
SMTP_USE_SSL=false           # exclusivo con STARTTLS
SMTP_FROM_EMAIL=notificaciones@repsecc.mx
SMTP_FROM_NAME=Cumplimiento REPSE
SMTP_REPLY_TO=               # opcional
SMTP_TIMEOUT_SECONDS=10
```

**Alternativas**:
- **SDK específico (boto3-ses, postmark-python)**: ataría el producto a un proveedor; rompería on-prem.
- **`smtplib` síncrono**: bloquea el event loop; con 2000 correos/día genera latencia innecesaria.
- **Servicio interno tipo "mail relay" propio**: invento innecesario; SMTP estándar lleva 40 años funcionando.

---

## 3. Templating de correo

**Decisión**: Jinja2 con dos templates por tipo de alerta: `.html.j2` (HTML con CSS inline) y `.txt.j2` (fallback texto plano). Ambos se envían en un `MIME multipart/alternative`.

**Diseño visual** (HTML):
- Paleta del producto (FR-016 del 001): azules profundos `#0B2545`, neutros `#F3F4F6`, acentos por estado.
- Una sola columna, max-width 600 px, sin imágenes externas (anti-spam, accesibilidad).
- Botón "Ver detalle" con `href` al detalle del documento.

**Tipos iniciales**:
1. `expiring_soon` — agrupa todos los docs "por vencer" del proveedor del día.
2. `expired` — agrupa todos los docs vencidos del proveedor del día.

**Variables de plantilla**: `{ org, supplier, documents: [{type_name, period, due_date, days_until_due, link}], unsubscribe_note }`.

**Alternativas**:
- **MJML**: produce HTML responsive bonito pero agrega un paso de build. Para v1 (correos operativos, no marketing) es overkill.
- **HTML hand-coded sin engine**: pierde la separación de datos/markup; difícil de internacionalizar (i18n queda para v2 pero el patrón debe permitirlo).

---

## 4. Idempotencia diaria

**Decisión**: clave única en `notifications`:

```sql
UNIQUE KEY uq_notif_org_doc_type_date (organization_id, document_id, alert_type, run_date)
```

Donde `run_date = DATE(now en tz del tenant)`. La función `evaluate_documents()` intenta `INSERT ... ON DUPLICATE KEY UPDATE` o atrapa `IntegrityError`. Si la clave ya existe, salta (la notificación de ese día ya se generó).

**Rationale**:
- Una sola fuente de verdad: la DB.
- Sobrevive a reinicios del scheduler a media corrida (re-ejecutar es seguro).
- No requiere Redis ni cache externo.

**Alternativas**:
- **Cache Redis SETNX con TTL 24h**: introduce un servicio para algo que MySQL ya hace correctamente.
- **Filesystem lock**: frágil ante reinicios y multi-réplica.

---

## 5. Manejo de zonas horarias por tenant

**Decisión**: `organizations.timezone` (heredado del 001) gobierna **dos cosas**: (a) la hora en la que corre el barrido diario; (b) la fecha que se usa como `run_date` para idempotencia y como `today` para evaluar "por vencer".

**Implementación**:
```python
def tenant_today(org: Organization) -> date:
    return datetime.now(ZoneInfo(org.timezone)).date()

def should_run_now(org: Organization, now_utc: datetime) -> bool:
    tz = ZoneInfo(org.timezone)
    local_now = now_utc.astimezone(tz)
    last_run = org.alert_config.last_run_at
    return (
        local_now.time() >= org.alert_config.daily_run_at
        and (last_run is None or last_run.astimezone(tz).date() < local_now.date())
    )
```

**Alternativas**:
- Forzar UTC en todos los cálculos: rompe la expectativa del usuario ("mis alertas llegan en la mañana, no a medianoche").
- Configurar tz por usuario en vez de tenant: complica el modelo, sin caso de uso claro.

---

## 6. Reintentos ante fallos SMTP

**Decisión**: `tenacity` con backoff exponencial: 1 min, 5 min, 25 min (3 intentos totales). Tras agotar, marca `Notification.status='failed'` y la entrada in-app sigue visible.

**Implementación**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=60, min=60, max=1500),
    retry=retry_if_exception_type((aiosmtplib.SMTPConnectError, aiosmtplib.SMTPServerDisconnected, asyncio.TimeoutError)),
    reraise=True,
)
async def send_email(...): ...
```

Errores **no retryables** (autenticación, recipient rechazado): se marca `failed` de inmediato sin reintentar.

**Alternativas**:
- **Dead letter queue**: añade infraestructura. La métrica `notifications_sent_total{result="failed"}` ya alerta al operador en Prometheus.
- **Reintentos sin límite**: riesgo de loop infinito si el SMTP está mal configurado.

---

## 7. Almacén y exposición de notificaciones in-app

**Decisión**: tabla `notifications` con columnas `(organization_id, recipient_user_id, type, payload_json, status, read_at, created_at)`. El frontend consulta `GET /api/v1/notifications?unread=true&limit=50` al cargar el header (cada login) y mediante polling pasivo cada 30 s mientras la pestaña esté activa (`document.visibilityState`).

**Diseño deliberado**:
- **No hay WebSocket** (FR del spec). El polling cubre el caso 95% (refrescos manuales, navegación).
- El estado "no leída / leída" lo cambia el endpoint `POST /notifications/{id}/mark-read`.
- Una notificación in-app puede referenciar múltiples documentos (campo `payload_json.document_ids`) cuando se agrupa por proveedor.

**Alternativas**:
- **WebSocket**: requiere hacer al backend stateful (sticky sessions o pub/sub). Fuera de alcance v1.
- **SSE**: alternativa a WebSocket; sigue requiriendo conexión persistente. No vale la pena para el caso de uso.

---

## 8. Privacidad de PII en bitácora

**Decisión**: en `audit_log.metadata`, los correos destinatarios se almacenan como `{ domain: "acme.com", local_hash: "a1b2c3" }` (primeros 6 chars del SHA-256 del local-part). Suficiente para auditar "¿se envió a contabilidad@acme.com?" sin retener PII completa.

**Rationale**:
- La constitución pide "mínima recolección de PII".
- Si en una investigación se necesita el correo exacto, sigue estando en el campo `recipient_email` de `notifications` (que tiene política de retención del tenant).

---

## Resumen de unknowns resueltos

| Tema | Decisión | Sección |
|------|----------|---------|
| Scheduler diario | APScheduler in-process, tick 5 min, jobstore en MySQL | §1 |
| Transporte de correo | SMTP genérico vía `aiosmtplib` | §2 |
| Templating | Jinja2 con HTML inline-CSS + texto plano | §3 |
| Idempotencia | DB unique constraint `(org, doc, type, run_date)` | §4 |
| Zonas horarias | `organizations.timezone` gobierna ejecución + idempotencia | §5 |
| Reintentos SMTP | `tenacity` 3 intentos backoff 1/5/25 min | §6 |
| Notificaciones in-app | Tabla MySQL + polling cada 30 s, sin WebSocket | §7 |
| Privacidad de PII | Hash + dominio en audit log; correo completo solo en `notifications` con retención del tenant | §8 |
