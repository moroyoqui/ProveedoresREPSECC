---
description: "Task list — Alertas y Recordatorios de Cumplimiento"
---

# Tasks: Alertas y Recordatorios de Cumplimiento

**Input**: Design documents from `/specs/002-compliance-alerts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (alert-config, alert-silences, notifications)

**Tests**: INCLUIDOS. La constitución (Principio III) y `contracts/README.md` exigen tests de contrato, multi-tenant negativo e idempotencia diaria para este feature (rutas críticas: scheduler, aislamiento de tenant).

**Organization**: Tareas agrupadas por user story para implementación y prueba independientes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede correr en paralelo (archivos distintos, sin dependencias incompletas)
- **[Story]**: US1, US2, US3
- Rutas exactas en cada tarea

## Path Conventions (de plan.md — web app)

- Backend: `backend/src/repse/alerts/` (módulo nuevo cohesivo), migraciones en `backend/src/repse/migrations/versions/`
- Backend tests: `backend/tests/{contract,integration,unit}/`
- Frontend: `frontend/src/`
- Ops: `ops/docker-compose.yml`, `.env.example`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Esqueleto del módulo, dependencias y configuración de entorno.

- [X] T001 Crear el esqueleto del módulo de alertas (`__init__.py`) en `backend/src/repse/alerts/` (los archivos reales se crean en su tarea de Phase 2)
- [X] T002 Agregar dependencias backend `aiosmtplib`, `jinja2` (runtime; `tenacity` ya existía) y `aiosmtpd`, `freezegun` (dev) a `backend/pyproject.toml` — NOTA: se omite `apscheduler` por seguir el patrón de job asyncio existente (`documents/jobs.py`)
- [X] T003 [P] Agregar settings de SMTP y scheduler (`smtp_*`, `alerts_scheduler_enabled`) en `backend/src/repse/config.py` (config es un módulo único, no `config/settings.py`)
- [X] T004 [P] Agregar el servicio `mailpit` a `ops/docker-compose.yml` (puertos 8025/1025) + passthrough de env al contenedor `app`, y las nuevas variables al `.env`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Motor de barrido, modelos, persistencia y wiring compartidos por TODAS las historias.

**⚠️ CRITICAL**: Ninguna historia puede comenzar hasta completar esta fase.

- [X] T005 Migración Alembic `0011_add_alerts` (4 tablas + índices + unique de dedup + downgrade) en `backend/alembic/versions/0011_add_alerts.py` — NOTA: nº 0011 (0010 ya existía); tabla renombrada a `supplier_alert_recipients` (la original excedía 64 chars en nombre de FK); idempotencia vía columna `dedup_key` + `UNIQUE(organization_id, dedup_key)` en vez de índice funcional sobre JSON
- [X] T006 Migración de datos `0012_seed_alert_config` (siembra `AlertConfig` para orgs existentes) en `backend/alembic/versions/0012_seed_alert_config.py`
- [X] T007 Los 4 modelos SQLAlchemy `AlertConfig`, `SupplierAlertRecipientOverride`, `AlertSilence`, `Notification` (TenantOwned) en `backend/src/repse/alerts/models.py` — validado: import + `configure_mappers()` OK, tablas registradas en metadata
- [X] T008 [P] Schemas Pydantic de los 3 contratos en `backend/src/repse/alerts/schemas.py` — validado
- [X] T009 Provisioning de organización extendido para sembrar `AlertConfig` por defecto en `backend/src/repse/supplier_types/provisioning.py` + registro del módulo en `backend/alembic/env.py`
- [X] T010 [P] Helpers de zona horaria por tenant `tenant_today(org)` y `should_run_now(org, config, now_utc)` en `backend/src/repse/alerts/service.py`
- [X] T011 [P] Cliente SMTP con reintentos `tenacity` en `backend/src/repse/alerts/smtp_client.py` — NOTA: `send_email` síncrono (vía `asyncio.run`) para el barrido en thread; backoff corto (s, no min) para no bloquear el batch — el retry largo queda para la CLI `retry-failed` (T051)
- [X] T012 [P] Loader Jinja2 (HTML inline-CSS + texto plano) + plantilla `alert.{html,txt}.j2` genérica en `backend/src/repse/alerts/render.py` + `templates/`
- [X] T013 [P] Resolver de destinatarios (default + override por proveedor) e in-app (usuarios back-office activos) en `backend/src/repse/alerts/recipients.py`
- [X] T014 [P] Generador de notificaciones in-app + `make_dedup_key` en `backend/src/repse/alerts/inapp.py`
- [X] T015 Evaluador núcleo + barrido `run_org_sweep`/`run_daily_alerts`: deriva requisitos por `SupplierType`, clasifica `expiring_soon`/`expired`, omite silenciados, persiste con idempotencia (`dedup_key`) y envía correo, en `backend/src/repse/alerts/service.py` — NOTA: "Faltante" queda para US2/T035; validado por import + `configure_mappers()`
- [X] T016 Scheduler `asyncio`-loop (tick 5 min, `ALERTS_SCHEDULER_ENABLED`) en `backend/src/repse/alerts/scheduler.py`, arrancado en el lifespan de `backend/src/repse/main.py` — sin APScheduler (patrón del repo)
- [X] T017 Router de alertas (stub) en `backend/src/repse/alerts/routes.py`, montado en `/api/v1/alerts` con guard back-office en `backend/src/repse/main.py`
- [ ] T018 [P] Crear fixtures/factories de prueba: sembrado cross-tenant de proveedores+documentos en estados y control de reloj con `freezegun`, en `backend/tests/conftest.py` (o `backend/tests/factories.py`)
- [ ] T019 Test de aislamiento multi-tenant del barrido: el scheduler corriendo para el tenant A NO crea notificaciones con datos del tenant B, en `backend/tests/integration/test_alerts_multitenant.py`

**Checkpoint**: motor de barrido, persistencia con dedup y aislamiento listos — las historias pueden comenzar.

---

## Phase 3: User Story 1 — Notificación automática previa al vencimiento (Priority: P1) 🎯 MVP

**Goal**: Emitir una notificación por **correo + in-app** para cada documento requerido cuya fecha de vencimiento efectiva cae dentro de la antelación configurada, una sola vez por día (idempotente), con enlace al detalle del documento.

**Independent Test**: Configurar antelación a 7 días y un documento que vence en 7 días; tras correr el barrido, el destinatario recibe exactamente un correo (visible en Mailpit) y aparece una entrada in-app; correr de nuevo el mismo día no duplica.

### Tests for User Story 1 ⚠️

- [ ] T020 [P] [US1] Tests de contrato de los endpoints de notificaciones (forma de respuesta, 401 sin sesión, 404 cross-tenant en mark-read, 403 viewer en trigger-now) en `backend/tests/contract/test_notifications_contract.py`
- [ ] T021 [P] [US1] Test de integración: un documento dentro de la ventana genera 1 correo + 1 in-app a cada destinatario el día correspondiente, en `backend/tests/integration/test_alerts_expiring.py`
- [ ] T022 [P] [US1] Test de idempotencia diaria: invocar el barrido dos veces el mismo día no crea filas duplicadas en `notifications`, en `backend/tests/integration/test_alerts_idempotency.py`

### Implementation for User Story 1

- [ ] T023 [US1] Implementar la regla de clasificación `expiring_soon` (vencimiento efectivo dentro de `expiring_lead_time_days`) dentro del evaluador en `backend/src/repse/alerts/service.py` (depende de T015)
- [ ] T024 [P] [US1] Crear los templates `expiring_soon.html.j2` y `expiring_soon.txt.j2` (paleta del producto, botón "Ver detalle" con enlace al documento) en `backend/src/repse/alerts/templates/`
- [ ] T025 [US1] Implementar el envío de correo agregado por proveedor/día (un solo correo con todos los documentos del proveedor) usando el SMTP client y los templates, en `backend/src/repse/alerts/service.py`
- [ ] T026 [US1] Generar la entrada in-app `expiring_soon` (payload con `supplier` + lista de documentos) en `backend/src/repse/alerts/inapp.py`
- [ ] T027 [US1] Implementar los endpoints `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/{id}/mark-read`, `POST /notifications/mark-all-read` en `backend/src/repse/alerts/routes.py`
- [ ] T028 [US1] Implementar el endpoint admin `POST /alerts/trigger-now` (encola job APScheduler, respeta idempotencia) en `backend/src/repse/alerts/routes.py`
- [ ] T029 [P] [US1] Crear el cliente API de notificaciones (list, unread-count, mark-read, mark-all-read) en `frontend/src/lib/api/notifications.ts`
- [ ] T030 [P] [US1] Crear los componentes `NotificationBell.tsx`, `NotificationCenter.tsx`, `NotificationItem.tsx` en `frontend/src/components/notifications/`
- [ ] T031 [US1] Integrar `NotificationBell` en el header de `frontend/src/components/layout/AppShell.tsx` con polling pasivo cada ~30 s (sensible a `document.visibilityState`)

**Checkpoint**: US1 funcional y testeable de forma independiente — MVP entregable.

---

## Phase 4: User Story 2 — Recordatorio diario de documentos vencidos (Priority: P1)

**Goal**: Para documentos vencidos (y faltantes requeridos por el `SupplierType`), emitir recordatorio **diario** por correo + in-app hasta que se renueven, el tipo deje de aplicar, o un usuario con permiso los silencie con motivo.

**Independent Test**: Marcar un documento como vencido; durante 3 días consecutivos (reloj con freezegun) se envía un recordatorio por día; al renovarlo, se detienen; al silenciarlo con motivo, se detienen y queda en bitácora.

### Tests for User Story 2 ⚠️

- [ ] T032 [P] [US2] Tests de contrato de los endpoints de silenciamiento (201 silence, 409 already_silenced, 404 no_active_silence, 403 viewer) en `backend/tests/contract/test_silences_contract.py`
- [ ] T033 [P] [US2] Test de integración: documento vencido genera 3 recordatorios en 3 días y se detiene al renovar, en `backend/tests/integration/test_alerts_expired.py`
- [ ] T034 [P] [US2] Test de integración: silenciar un documento detiene sus recordatorios mientras el silencio esté activo, en `backend/tests/integration/test_alerts_silence.py`

### Implementation for User Story 2

- [ ] T035 [US2] Implementar la regla de clasificación `expired` y la detección de "Faltante" (tipo requerido sin documento `is_latest` para el periodo vigente) en el evaluador en `backend/src/repse/alerts/service.py` (depende de T015)
- [ ] T036 [US2] Garantizar el comportamiento de recordatorio diario (nueva fila por `run_date`, sin duplicar dentro del mismo día) para `expired` en `backend/src/repse/alerts/service.py`
- [ ] T037 [P] [US2] Crear los templates `expired.html.j2` y `expired.txt.j2` en `backend/src/repse/alerts/templates/`
- [ ] T038 [US2] Implementar el servicio de silenciamiento (`silence`, `unsilence`, auto-levante con `ended_reason='document_renewed'`/`'type_retired'`, bump de `documents.last_updated_*`, bitácora) en `backend/src/repse/alerts/silences.py`
- [ ] T039 [US2] Implementar los endpoints `POST /documents/{id}/silence`, `POST /documents/{id}/unsilence`, `GET /documents/{id}/silences`, `GET /alert-silences` en `backend/src/repse/alerts/routes.py`
- [ ] T040 [P] [US2] Crear el componente `SilenceDialog.tsx` (captura de motivo 5..500 chars) en `frontend/src/components/documents/SilenceDialog.tsx`
- [ ] T041 [US2] Integrar la acción de silenciar/levantar en el detalle/listado de documentos del proveedor en `frontend/src/components/documents/` (botón que abre `SilenceDialog`)

**Checkpoint**: US1 y US2 funcionan independientemente; el motor cubre por-vencer y vencido con silenciamiento.

---

## Phase 5: User Story 3 — Configuración de antelación y destinatarios (Priority: P2)

**Goal**: Que un administrador configure por organización la antelación, los destinatarios por defecto y el horario del barrido; y que gestor/admin definan destinatarios específicos por proveedor que sobrescriban los predeterminados.

**Independent Test**: Cambiar la antelación de 15 a 7 días y los destinatarios; la siguiente corrida evalúa contra 7 días y envía a los nuevos destinatarios. Definir override en un proveedor y verificar que sus alertas van a esos correos.

### Tests for User Story 3 ⚠️

- [ ] T042 [P] [US3] Tests de contrato de `/alerts/config` (GET/PATCH, 403 viewer/manager en PATCH, validaciones 1..90 y emails) y de `/suppliers/{id}/alert-recipients` (GET/PUT/DELETE, 400 array vacío) en `backend/tests/contract/test_alert_config_contract.py`
- [ ] T043 [P] [US3] Test de integración: cambiar `expiring_lead_time_days` y `default_recipient_emails` aplica en la siguiente corrida sin redeploy, en `backend/tests/integration/test_alerts_config.py`

### Implementation for User Story 3

- [ ] T044 [US3] Implementar el servicio de configuración (`get_config`, `update_config` con validaciones) en `backend/src/repse/alerts/service.py`
- [ ] T045 [US3] Implementar los endpoints `GET /alerts/config` y `PATCH /alerts/config` (PATCH solo admin) en `backend/src/repse/alerts/routes.py`
- [ ] T046 [US3] Implementar el servicio + endpoints de override por proveedor `GET/PUT/DELETE /suppliers/{id}/alert-recipients` en `backend/src/repse/alerts/recipients.py` y `backend/src/repse/alerts/routes.py`
- [ ] T047 [P] [US3] Crear la página de configuración de alertas (antelación, destinatarios, horario, enabled) en `frontend/src/pages/settings/alerts.tsx`
- [ ] T048 [US3] Agregar la UI de destinatarios específicos por proveedor en la edición del proveedor en `frontend/src/pages/suppliers/edit.tsx`

**Checkpoint**: las tres historias quedan funcionales e independientes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observabilidad, bitácora con PII redactada, operación y validación final.

- [ ] T049 [P] Registrar en `audit_log` cada envío y silenciamiento con PII redactada (`{domain, local_hash}`) usando `redact_pii` del 001, en `backend/src/repse/alerts/service.py` y `backend/src/repse/alerts/silences.py`
- [ ] T050 [P] Exponer métricas Prometheus `notifications_sent_total{channel,result}`, `notifications_pending`, `daily_run_duration_seconds{org_id}` en `backend/src/repse/alerts/scheduler.py`
- [ ] T051 [P] Crear la CLI de operación (`retry-failed --org`, `test-smtp <email>`) en `backend/src/repse/alerts/cli.py`
- [ ] T052 [P] Tests unitarios de los helpers de zona horaria y del resolver de destinatarios en `backend/tests/unit/test_alerts_helpers.py`
- [ ] T053 Ejecutar la validación E2E de `quickstart.md` (configurar → sembrar doc → trigger-now → verificar Mailpit + in-app → idempotencia → silenciar)
- [ ] T054 [P] Actualizar documentación operativa de alertas en `docs/` (o README del módulo)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — empieza de inmediato.
- **Foundational (Phase 2)**: depende de Setup — BLOQUEA todas las historias.
- **User Stories (Phase 3–5)**: dependen de Foundational. Tras él pueden ir en paralelo (si hay equipo) o secuenciales por prioridad (US1 → US2 → US3).
- **Polish (Phase 6)**: depende de las historias deseadas completas.

### User Story Dependencies

- **US1 (P1)**: arranca tras Foundational. Sin dependencia de otras historias. Es el MVP.
- **US2 (P1)**: arranca tras Foundational. Comparte el evaluador (T015) con US1 pero su regla `expired` y el silenciamiento son independientes y testeables solos.
- **US3 (P2)**: arranca tras Foundational. La config afecta el comportamiento de US1/US2 pero se prueba de forma independiente (cambio aplica en la siguiente corrida).

### Within Each User Story

- Tests primero (deben fallar antes de implementar).
- Modelos → servicios → endpoints → integración frontend.

### Parallel Opportunities

- Setup: T003, T004 en paralelo.
- Foundational: T008, T010, T011, T012, T013, T014, T018 en paralelo (archivos distintos) una vez creado el esqueleto (T001) y los modelos (T007) donde aplique.
- Tras Foundational: US1, US2 y US3 pueden trabajarse en paralelo por distintas personas.
- Dentro de cada historia, las tareas marcadas [P] (tests, templates, componentes frontend) corren en paralelo.

---

## Parallel Example: User Story 1

```bash
# Tests de US1 juntos:
Task: "Contract tests notificaciones en backend/tests/contract/test_notifications_contract.py"   # T020
Task: "Integration expiring en backend/tests/integration/test_alerts_expiring.py"                 # T021
Task: "Idempotencia en backend/tests/integration/test_alerts_idempotency.py"                      # T022

# Trabajo paralelo de US1 (archivos distintos):
Task: "Templates expiring_soon en backend/src/repse/alerts/templates/"                            # T024
Task: "API client en frontend/src/lib/api/notifications.ts"                                        # T029
Task: "Componentes NotificationBell/Center/Item en frontend/src/components/notifications/"         # T030
```

---

## Implementation Strategy

### MVP First (solo User Story 1)

1. Completar Phase 1: Setup.
2. Completar Phase 2: Foundational (CRÍTICO — bloquea todo).
3. Completar Phase 3: User Story 1.
4. **PARAR Y VALIDAR**: probar US1 de forma independiente (correo en Mailpit + in-app + idempotencia).
5. Desplegar/demostrar si está listo.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → probar → demo (MVP de alertas por-vencer).
3. US2 → probar → demo (recordatorios de vencidos + silenciamiento).
4. US3 → probar → demo (configuración y overrides).

### Parallel Team Strategy

Tras Foundational: Dev A en US1, Dev B en US2, Dev C en US3; integran de forma independiente.

---

## Notes

- [P] = archivos distintos, sin dependencias incompletas.
- La idempotencia diaria depende del unique constraint de `notifications` (T005) — no debe resolverse en lógica de aplicación.
- Aislamiento multi-tenant: verificar T019 antes de mergear cualquier historia (Principio II de la constitución).
- Commit tras cada tarea o grupo lógico.
