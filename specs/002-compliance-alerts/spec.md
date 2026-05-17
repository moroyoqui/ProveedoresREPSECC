# Feature Specification: Alertas y Recordatorios de Cumplimiento

**Feature Branch**: `002-compliance-alerts`

**Created**: 2026-05-16

**Status**: Draft

**Depends on**: [`001-repse-compliance-tracker`](../001-repse-compliance-tracker/spec.md) (entidades `Proveedor`, `Documento Cargado`, `Tipo de Documento de Cumplimiento`, `Usuario`, `Bitácora`, y reglas FR-009, FR-009a, FR-012, FR-013).

## Scope

Cierra el ciclo de gestión de cumplimiento añadiendo **alertas proactivas** sobre la información que ya almacena el spec 001. Sin este spec, el cliente tendría que revisar el tablero manualmente para detectar vencimientos. Cubre:

- Envío de notificaciones por **correo electrónico** y **dentro de la aplicación** cuando un documento está por vencer o ya venció.
- Configuración por organización: antelación (días previos), destinatarios y silenciamiento por documento.
- Bitácora de envíos y fallos.

Fuera de alcance de este spec: canales WhatsApp/SMS, escalamiento jerárquico, integraciones con Slack/Teams.

## Clarifications

Aplica el bloque de **clarificaciones globales** definido en el spec 001 (sesión 2026-05-16). Ver [`001-repse-compliance-tracker/spec.md#clarifications`](../001-repse-compliance-tracker/spec.md#clarifications). Resumen relevante para este spec:

- Solo el cliente contratante accede al sistema (no hay portal de proveedor); las alertas se dirigen a usuarios del tenant únicamente.
- Las notificaciones del MVP se envían por **correo electrónico** y se muestran **in-app**. Otros canales quedan fuera de alcance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Notificación automática previa al vencimiento (Priority: P1)

Un usuario configura la antelación (p. ej. 15 días) y los destinatarios para las alertas de la organización. El sistema evalúa diariamente cada documento con vigencia y envía una notificación por correo y dentro de la app cuando entra dentro de la ventana configurada. El destinatario recibe el correo con un enlace directo al detalle del documento, y la alerta también aparece en el centro de notificaciones del tenant.

**Why this priority**: Es la razón de ser de este spec; sin notificación proactiva, no hay valor diferencial frente al tablero del 001.

**Independent Test**: Configurar antelación a 7 días y un documento que vence en 7 días; al correr el proceso diario, el destinatario recibe exactamente un correo y la alerta aparece en la app.

**Acceptance Scenarios**:

1. **Given** un documento que vencerá en 15 días y una configuración de alerta a 15 días, **When** corre el proceso diario de evaluación, **Then** se envía exactamente una notificación por correo a cada destinatario configurado y se crea una entrada in-app, en el día correspondiente.
2. **Given** un documento dentro de la ventana de alerta, **When** ya se envió la notificación del día, **Then** no se vuelve a enviar otra notificación para ese mismo día y documento (idempotencia diaria).
3. **Given** un usuario que renueva el documento dentro del periodo de alerta cargando un archivo nuevo vigente, **When** el sistema recalcula el estado, **Then** se detienen automáticamente los recordatorios para ese documento.

---

### User Story 2 - Recordatorio diario de documentos vencidos (Priority: P1)

Para documentos ya vencidos, el sistema envía un recordatorio diario al/los destinatario(s) hasta que el documento sea renovado, el tipo deje de aplicar al proveedor, o un usuario con permiso silencie la alerta con una nota.

**Why this priority**: Un documento vencido representa exposición legal/operativa. El recordatorio diario es la presión necesaria para forzar la renovación.

**Independent Test**: Marcar un documento como vencido y verificar que durante 3 días consecutivos se envía recordatorio; al renovarlo, los recordatorios se detienen.

**Acceptance Scenarios**:

1. **Given** un documento vencido sin renovación, **When** corren tres procesos diarios consecutivos, **Then** se envían tres notificaciones (una por día) a los destinatarios configurados.
2. **Given** un documento vencido, **When** un usuario con permiso lo silencia con una nota, **Then** se detienen los recordatorios mientras el silenciamiento esté activo y queda registro en bitácora con usuario, fecha y motivo.

---

### User Story 3 - Configuración de antelación y destinatarios por la organización (Priority: P2)

Un administrador define en la organización: la antelación por defecto (en días) para alertas de "por vencer", la lista de destinatarios por defecto (al menos un correo), y opcionalmente sobrescribe estos valores por proveedor.

**Why this priority**: Sin configuración, las alertas usarían valores hardcodeados; la organización necesita poder reflejar su política interna (área de compras, jurídico, etc.).

**Independent Test**: Cambiar la antelación de 15 a 7 días y verificar que las próximas alertas se envían 7 días antes del vencimiento; cambiar destinatarios y verificar que el cambio aplica al siguiente envío.

**Acceptance Scenarios**:

1. **Given** un administrador en configuración, **When** cambia la antelación a 7 días, **Then** la próxima ejecución diaria evalúa contra 7 días y no contra el valor anterior.
2. **Given** un proveedor con destinatarios específicos definidos, **When** se genera una alerta para sus documentos, **Then** los correos van a esos destinatarios y no a los predeterminados de la organización.

---

### Edge Cases

- ¿Qué pasa si la antelación se cambia a un valor que ya pasó la fecha de vencimiento? El documento ya está "vencido"; el sistema no envía una alerta retroactiva de "por vencer", solo aplica el recordatorio de vencido.
- ¿Qué pasa si el correo de notificación no se entrega? El sistema registra el fallo, reintenta hasta un número máximo (al menos 3) con backoff; la notificación in-app sigue visible aunque el correo falle.
- ¿Qué pasa si un destinatario es removido entre el cálculo y el envío? La notificación se envía solo a los destinatarios vigentes en el momento del envío.
- ¿Qué pasa si dos documentos del mismo proveedor cumplen condición de alerta el mismo día? Se envía un solo correo agregando ambos documentos, no dos correos separados (anti-spam).
- ¿Qué pasa si el proceso diario falla a media corrida? Al reintentarse, la idempotencia diaria evita envíos duplicados sobre los documentos ya notificados ese día.
- ¿Qué pasa si un proveedor está inactivo? No se generan alertas para sus documentos.
- ¿Qué pasa si un tipo de documento es desactivado en el catálogo? Las alertas dejan de generarse para ese tipo desde el siguiente día.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ejecutar al menos una vez al día (en horario local del tenant configurable, por defecto 08:00) un proceso que recalcule el estado de cada documento con vigencia y determine si corresponde generar alertas.
- **FR-002**: El sistema DEBE generar una notificación de "por vencer" para todo documento cuya fecha de vencimiento efectiva caiga dentro de la antelación configurada por la organización (por defecto 15 días) y aún no haya recibido alerta ese día.
- **FR-003**: El sistema DEBE generar una notificación de "vencido" diaria para todo documento con fecha de vencimiento ya superada, mientras no esté silenciado y no haya sido renovado.
- **FR-004**: Cada notificación DEBE entregarse en **dos canales** simultáneamente: (a) correo electrónico al/los destinatario(s), y (b) entrada in-app visible en el centro de notificaciones del tenant.
- **FR-005**: El sistema DEBE agrupar en un único correo todas las alertas del mismo proveedor que se generan el mismo día para los mismos destinatarios, en lugar de enviar un correo por documento.
- **FR-006**: El sistema DEBE evitar envíos duplicados: una vez generada y enviada (o intentada) una alerta para un documento en un día determinado, no se reintenta esa misma alerta hasta el siguiente día calendario.
- **FR-007**: Un administrador DEBE poder configurar a nivel organización: (a) antelación en días para alertas "por vencer", (b) lista de destinatarios por defecto (uno o más correos válidos), (c) horario diario de ejecución del proceso de evaluación.
- **FR-008**: Un gestor o administrador DEBE poder definir destinatarios específicos por proveedor que sobrescriban los predeterminados de la organización.
- **FR-009**: Un usuario con permiso DEBE poder silenciar las alertas de un documento individual aportando un motivo en texto libre; el silenciamiento persiste hasta que el documento se renueva, se levanta manualmente o el tipo deja de aplicar.
- **FR-010**: El sistema DEBE registrar en bitácora cada envío de notificación (destinatario, canal, documento, resultado de entrega) y cada silenciamiento (usuario, motivo, fecha).
- **FR-011**: Ante fallo de entrega de correo, el sistema DEBE reintentar al menos 3 veces con backoff incremental; tras agotar reintentos, marca el envío como fallido y deja la notificación in-app visible.
- **FR-012**: Cada correo DEBE incluir un enlace directo al detalle del documento dentro de la aplicación, requiriendo sesión válida para acceder al archivo.
- **FR-013**: La operación de notificación DEBE respetar el aislamiento multi-tenant: nunca un destinatario recibe información sobre proveedores o documentos de otra organización.

### Key Entities

- **Configuración de Alertas (por Organización)**: Atributos: antelación por defecto (días), destinatarios por defecto (lista de correos), horario de ejecución, zona horaria.
- **Configuración de Destinatarios por Proveedor** (opcional): Atributos: proveedor, lista de correos que sobrescriben los predeterminados.
- **Silenciamiento de Alerta**: Atributos: documento, usuario que silenció, motivo, fecha de inicio, fecha de fin (calculada o null).
- **Notificación**: Atributos: documento(s) referenciados, destinatario, canal (correo / in-app), tipo (por vencer / vencido), fecha de envío, estado de entrega (pendiente / enviada / fallida / leída), intentos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los documentos con vigencia que entran a la ventana de alerta configurada genera al menos una notificación (correo e in-app) en el día correspondiente.
- **SC-002**: Cero notificaciones duplicadas: no se envía más de una alerta por documento, día y destinatario.
- **SC-003**: Cero fugas entre tenants: ningún destinatario recibe información sobre documentos de organizaciones distintas a la suya, validado en pruebas automatizadas.
- **SC-004**: 95% de los correos de alerta se entregan exitosamente al primer intento en condiciones normales del proveedor de correo; los fallidos completan reintentos en menos de 24 horas.
- **SC-005**: Un administrador puede cambiar la antelación o la lista de destinatarios y ver el efecto en la siguiente ejecución diaria, sin requerir despliegue.

## Assumptions

- El proceso de evaluación diaria se ejecuta en una zona horaria configurable por tenant; por defecto, horario de Ciudad de México.
- El sistema de envío de correo se contrata como servicio externo confiable (Postmark, SendGrid, SES o equivalente) y queda definido en el plan técnico.
- No hay envío push ni SMS en v1; solo correo + in-app.
- Las alertas in-app no requieren WebSocket en v1; basta con que se reflejen al refrescar o navegar a la sección.
- Si un destinatario quiere darse de baja, su administrador lo remueve manualmente; no hay link "unsubscribe" público en v1 (porque las alertas son comunicaciones operativas, no marketing).
