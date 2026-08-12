# Contract: Alert Silences

Silenciamiento manual por documento (FR-009).

## POST `/api/v1/documents/{document_id}/silence`

Silencia las alertas de un documento.

- **Auth**: requerida. **Roles**: admin, manager.
- **Body**:
  ```json
  { "reason": "Documento en revisión por contador externo hasta fin de mes." }
  ```
- **Validaciones**:
  - `reason`: 5..500 chars.
  - El documento debe pertenecer al tenant.
  - No puede haber otro silenciamiento activo (`ended_at IS NULL`) para el mismo documento — si lo hay, responde `409 already_silenced` con el id del existente.
- **Respuesta** `201`:
  ```json
  {
    "id": 22,
    "document_id": 4521,
    "reason": "Documento en revisión por contador externo hasta fin de mes.",
    "started_at": "2026-05-17T09:14:00.000-06:00",
    "silenced_by": { "id": 42, "display_name": "Ana López" }
  }
  ```
- **Side effects**: bumpea `documents.last_updated_by/at` (es un cambio humano sobre el documento, ver spec 001 FR-011a). Registra `document.alert_silenced` en bitácora.

## POST `/api/v1/documents/{document_id}/unsilence`

Levanta el silenciamiento activo de un documento.

- **Auth**: requerida. **Roles**: admin, manager.
- **Body**:
  ```json
  { "reason": "Revisión completada." }
  ```
  `reason` es opcional (max 500 chars); se guarda en `audit_log`.
- **Respuesta** `200`:
  ```json
  {
    "id": 22,
    "ended_at": "2026-05-17T16:00:00.000-06:00",
    "ended_by": { "id": 42, "display_name": "Ana López" },
    "ended_reason": "manual"
  }
  ```
- **Errores**: `404 no_active_silence` si no hay silenciamiento activo.

## GET `/api/v1/documents/{document_id}/silences`

Lista historial de silenciamientos (activos + cerrados) del documento.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`: lista cronológica.

## GET `/api/v1/alert-silences`

Lista todos los silenciamientos activos del tenant (admin / manager).

- **Auth**: requerida. **Roles**: admin, manager.
- **Query params**: `cursor`, `limit` (default 50), `active_only` (default `true`).
- **Respuesta** `200`: lista paginada con `document`, `supplier`, `reason`, `started_at`, `silenced_by`.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /documents/{id}/silences | ✅ | ✅ | ✅ |
| GET /alert-silences | 403 | ✅ | ✅ |
| POST /documents/{id}/silence | 403 | ✅ | ✅ |
| POST /documents/{id}/unsilence | 403 | ✅ | ✅ |
