# Implementation Plan: Alertas y Recordatorios de Cumplimiento

**Branch**: `002-compliance-alerts` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from [./spec.md](./spec.md)

**Note**: Plan generado por `/speckit-plan`. Hereda el stack del [plan del spec 001](../001-repse-compliance-tracker/plan.md); este documento solo describe lo nuevo y específico para alertas.

## Summary

Añadir un motor de alertas proactivas sobre la bóveda de cumplimiento del spec 001. Un proceso diario ejecuta por cada tenant (en su zona horaria) un barrido sobre los documentos requeridos por el `SupplierType` de cada proveedor activo y emite notificaciones en **dos canales simultáneos**: correo electrónico (vía SMTP, agnóstico del proveedor) y entrada in-app en el centro de notificaciones del tenant. Las alertas son configurables por organización (antelación, destinatarios, horario), sobreescribibles por proveedor, y silenciables a nivel documento. Idempotencia diaria garantizada por una clave única `(org, doc, tipo de alerta, fecha)`. Reintentos con backoff ante fallo de correo. Sin canales push/SMS/WhatsApp.

## Technical Context

Hereda del [plan 001](../001-repse-compliance-tracker/plan.md): Python 3.12 + FastAPI + SQLAlchemy 2.x + MySQL 8 + Alembic + React 18 + Tailwind. Adiciones específicas:

**Language/Version**: sin cambios.

**Primary Dependencies (nuevas)**:
- **Backend**: `apscheduler` (in-process scheduler), `aiosmtplib` (cliente SMTP async), `jinja2` (templates de correo y de notificación in-app), `tenacity` (políticas de reintento declarativas).
- **Frontend**: sin libs nuevas; reutiliza Tanstack Query + componentes existentes.

**Storage**: mismas tablas + 4 nuevas (ver [data-model.md](./data-model.md)). Cero cambios al storage de archivos.

**Testing**: pytest + pytest-asyncio + factory_boy (sembrado de documentos en estados); pytest-freezegun para fijar `today` en tests del scheduler; aiosmtpd como servidor SMTP en memoria para tests del cliente.

**Target Platform**: sin cambios (Linux, Docker Compose on-prem). La instancia de `app` corre el scheduler como background task del proceso uvicorn. **No requiere proceso separado** ni Celery/Redis.

**Project Type**: web app (extiende el backend del 001 y el frontend).

**Performance Goals**:
- SC-001: 100% de documentos en ventana de alerta genera notificación dentro del día.
- SC-002: cero duplicados (constraint unique).
- SC-004: 95% de correos se entregan al primer intento; los demás completan retries en <24 h.
- p95 del barrido diario: <60 s por tenant de 500 proveedores × 50 docs vigentes = ~25 000 documentos a evaluar; aceptable porque el cálculo es por documento + UN INSERT por nueva notificación.

**Constraints**:
- **Idempotencia diaria** garantizada por DB unique constraint, no por lógica de aplicación.
- **SMTP genérico**: cliente final provee credenciales SMTP. El producto no asume SES/Postmark/SendGrid. Operador on-prem puede correr Postfix en Docker si quiere relay propio.
- **Zona horaria por tenant**: el cron respeta `organizations.timezone`. Un mismo segundo de tiempo absoluto puede ser "08:00 hoy" para un tenant y "09:00 hoy" para otro.
- **Sin WebSocket**: notificaciones in-app se materializan en la DB y el front las consulta al cargar la página o vía polling pasivo (~30 s) en el header.

**Scale/Scope**:
- ~20 organizaciones × 25 000 documentos vigentes = ~500 000 documentos a evaluar diariamente. Con índices apropiados es trivial.
- Volumen esperado de correos: pico estacional 1 000–2 000 correos/día agregado entre tenants (fin de mes/bimestre).

## Constitution Check

*GATE: pasa antes de research. Re-evalúa post-design.*

| Principio | Estado | Cómo se cumple en este spec |
|-----------|--------|------------------------------|
| **I. Secure by Default** | ✅ Pass | SMTP con STARTTLS obligatorio cuando `SMTP_PORT != 25` interno; credenciales en env vars; el enlace dentro del correo es a `/suppliers/{id}/documents/{id}` y requiere sesión válida (FR-019 del 001); no se incluyen contraseñas, tokens ni payloads completos en ningún correo. |
| **II. Multi-Tenant Data Isolation** | ✅ Pass | Cada notificación lleva `organization_id` NOT NULL. Mixin `TenantOwned` aplica. Constraint unique `(org, doc, type, date)` previene duplicado entre tenants accidentalmente. El scheduler itera tenant por tenant. |
| **III. Test-First for Critical Paths** | ✅ Pass | Tests del scheduler (idempotencia, no cross-tenant, reintentos), del SMTP client (mockeable con aiosmtpd) y de la regla de derivación "documento requerido por SupplierType" son obligatorios. |
| **IV. Observability** | ✅ Pass | Cada notificación se registra en bitácora (envío exitoso, fallo, silenciamiento). Métricas: `notifications_sent_total{channel,result}`, `notifications_pending`, `daily_run_duration_seconds{org_id}`. |
| **V. Simplicity & YAGNI** | ✅ Pass | APScheduler in-process (sin Celery+Redis), SMTP estándar (sin SDK por proveedor), MySQL (sin queues externas). Si la métrica de duración del job supera el SLO, se escala a worker dedicado. |

**Security & Compliance**: las direcciones de correo destinatarias son PII; en `audit_log` solo guardamos el dominio + un hash truncado para auditoría sin retener correo plano. Cualquier dato adicional se redacta vía `redact_pii` del 001. ✅

**Resultado**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-compliance-alerts/
├── spec.md                # Especificación
├── plan.md                # Este archivo
├── research.md            # Phase 0
├── data-model.md          # Phase 1
├── quickstart.md          # Phase 1
├── contracts/             # Phase 1
│   ├── alert-config.md
│   ├── alert-silences.md
│   └── notifications.md
├── checklists/
│   └── requirements.md
└── tasks.md               # Phase 2 (NO creado aquí)
```

### Source Code (repository root)

Se añaden módulos al backend del 001 y un componente al frontend. Nada se rompe; las entidades existentes solo se consumen.

```text
backend/
└── src/repse/
    └── alerts/                          # NUEVO módulo
        ├── __init__.py
        ├── models.py                    # AlertConfig, AlertRecipientOverride, AlertSilence, Notification, NotificationRun
        ├── schemas.py
        ├── service.py                   # Reglas de negocio: evaluate_documents, send_aggregated_email
        ├── scheduler.py                 # APScheduler setup + tarea diaria por tenant
        ├── smtp_client.py               # aiosmtplib wrapper
        ├── templates/                   # Jinja2 templates HTML+text
        │   ├── expiring_soon.html.j2
        │   ├── expiring_soon.txt.j2
        │   ├── expired.html.j2
        │   └── expired.txt.j2
        ├── recipients.py                # Resolver: org default + per-supplier override
        ├── silences.py                  # Silenciamiento por documento
        ├── inapp.py                     # Generador de entradas in-app
        └── routes.py                    # Endpoints REST

frontend/
└── src/
    ├── pages/
    │   └── settings/
    │       └── alerts.tsx               # Configuración por organización
    └── components/
        ├── notifications/
        │   ├── NotificationBell.tsx     # Indicador en el header
        │   ├── NotificationCenter.tsx   # Lista en panel lateral
        │   └── NotificationItem.tsx
        └── documents/
            └── SilenceDialog.tsx        # Silenciar alerta de un documento
```

**Structure Decision**: módulo cohesivo `backend/src/repse/alerts/` con todo lo del feature. El scheduler arranca con el lifespan del FastAPI app (no proceso separado). Frontend agrega 1 página de configuración + 3 componentes en el shell existente.

## Complexity Tracking

| Decisión | Por qué se aparta del default | Alternativa simple rechazada porque |
|----------|------------------------------|-------------------------------------|
| **APScheduler in-process en lugar de cron de OS** | El operador on-prem no debería instalar cron jobs separados. El binario `app` se autocontiene. | systemd timer / cron del host: añade fricción al despliegue Docker y rompe la portabilidad. |
| **Daily run en background task de FastAPI en vez de worker dedicado** | YAGNI: con 20 organizaciones, el barrido entero termina en <30 s. Mientras el proceso uvicorn esté vivo, el scheduler también. | Celery + beat + Redis introduce 2 servicios extra sin ganancia visible para v1. Se introduce solo si el barrido supera el SLO de 60 s o si pasa a multi-réplica. |
| **SMTP genérico en lugar de SDK por proveedor** | On-prem heterogéneo: algunos clientes querrán SES, otros Postmark, otros su SMTP corporativo. SMTP es el lowest common denominator. | SDK específico (ej. boto3-ses) ataría el producto a un proveedor cloud y rompería el requisito on-prem. |
| **Idempotencia por DB unique constraint en vez de cache distribuido** | Una sola fuente de verdad, consistente con el resto del producto (MySQL es ya parte del stack). | Redis SETNX agrega un servicio para resolver un problema que la DB ya resuelve. |

---

**Phase 0**: ver [research.md](./research.md).

**Phase 1**: ver [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).
