# Contract: In-App Notifications

Centro de notificaciones del usuario. Alimenta el indicador del header y el panel lateral del shell.

## GET `/api/v1/notifications`

Lista las notificaciones in-app del usuario actual.

- **Auth**: requerida. **Roles**: cualquiera.
- **Query params**:
  - `unread_only`: `true` (default) | `false`.
  - `cursor`, `limit` (default 50, máx 200).
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 1024,
        "type": "expiring_soon",
        "status": "sent",
        "supplier": { "id": 12, "legal_name": "Servicios Industriales del Norte SA de CV" },
        "documents": [
          {
            "id": 4521,
            "document_type_name": "Opinión SAT",
            "period_label": "Abril 2026",
            "due_date": "2026-05-31",
            "days_until_due": 14,
            "detail_url": "/suppliers/12/documents/4521"
          }
        ],
        "created_at": "2026-05-17T08:00:14.231Z",
        "read_at": null
      }
    ],
    "unread_count_total": 4,
    "next_cursor": null,
    "has_more": false
  }
  ```

## GET `/api/v1/notifications/unread-count`

Endpoint ligero usado por el polling del header (cada ~30 s).

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`:
  ```json
  { "unread_count": 4, "checked_at": "2026-05-17T15:23:11.000-06:00" }
  ```

## POST `/api/v1/notifications/{id}/mark-read`

Marca una notificación como leída.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `204`.
- **Errores**: `404` si la notificación no es del usuario actual o pertenece a otro tenant.

## POST `/api/v1/notifications/mark-all-read`

Marca todas las notificaciones del usuario como leídas.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`:
  ```json
  { "marked_count": 4 }
  ```

## POST `/api/v1/alerts/trigger-now`

Solo administradores. Fuerza una ejecución inmediata del barrido para el tenant actual (útil para validar configuración tras cambios). No bypassa la idempotencia diaria.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `202`:
  ```json
  {
    "job_id": "manual-7-20260517-152311",
    "scheduled_at": "2026-05-17T15:23:11.000-06:00",
    "status": "queued"
  }
  ```
- **Side effect**: encola un job de APScheduler con `id=manual-...` que corre en background. El estado final se refleja en `AlertConfig.last_run_*` y en métricas.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /notifications | ✅ | ✅ | ✅ |
| GET /notifications/unread-count | ✅ | ✅ | ✅ |
| POST /notifications/{id}/mark-read | ✅ | ✅ | ✅ |
| POST /notifications/mark-all-read | ✅ | ✅ | ✅ |
| POST /alerts/trigger-now | 403 | 403 | ✅ |
