# Contract: Alert Configuration

Configuración por organización (FR-007) y sobrescritura por proveedor (FR-008).

## GET `/api/v1/alerts/config`

Devuelve la configuración del tenant.

- **Auth**: requerida. **Roles**: cualquiera (lectura).
- **Respuesta** `200`:
  ```json
  {
    "id": 7,
    "expiring_lead_time_days": 15,
    "default_recipient_emails": ["compliance@repsecc.mx", "compras@repsecc.mx"],
    "daily_run_at": "08:00:00",
    "timezone": "America/Mexico_City",
    "enabled": true,
    "last_run_at": "2026-05-17T08:00:14.231Z",
    "last_run_status": "success"
  }
  ```

## PATCH `/api/v1/alerts/config`

Actualiza configuración.

- **Auth**: requerida. **Roles**: admin.
- **Body** (cualquier subset):
  ```json
  {
    "expiring_lead_time_days": 7,
    "default_recipient_emails": ["compliance@repsecc.mx"],
    "daily_run_at": "09:30:00",
    "enabled": true
  }
  ```
- **Validaciones**:
  - `expiring_lead_time_days`: 1..90.
  - `default_recipient_emails`: array no vacío, cada entrada email RFC válido.
  - `daily_run_at`: `HH:MM:SS` 00:00:00..23:59:59.
  - `enabled`: bool.
- **Respuesta** `200`: config actualizada.
- **Side effect**: el siguiente tick del scheduler recoge los nuevos valores automáticamente. No se re-encolan notificaciones ya enviadas hoy.
- **Errores**: `400 validation_error`, `403 forbidden`.

## GET `/api/v1/suppliers/{supplier_id}/alert-recipients`

Devuelve sobrescritura de destinatarios para un proveedor, o `null` si no hay.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`:
  ```json
  { "supplier_id": 12, "recipient_emails": ["legal@sin.mx"], "inherited_from_default": false }
  ```
  o cuando no hay override:
  ```json
  { "supplier_id": 12, "recipient_emails": ["compliance@repsecc.mx"], "inherited_from_default": true }
  ```

## PUT `/api/v1/suppliers/{supplier_id}/alert-recipients`

Crea o reemplaza la sobrescritura.

- **Auth**: requerida. **Roles**: admin, manager.
- **Body**:
  ```json
  { "recipient_emails": ["legal@sin.mx", "responsable-sin@repsecc.mx"] }
  ```
- **Respuesta** `200`: override aplicado.
- **Errores**: `400 validation_error` si el array está vacío (use DELETE para eliminar override).

## DELETE `/api/v1/suppliers/{supplier_id}/alert-recipients`

Elimina la sobrescritura. El proveedor vuelve a usar `default_recipient_emails`.

- **Auth**: requerida. **Roles**: admin, manager.
- **Respuesta** `204`.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /alerts/config | ✅ | ✅ | ✅ |
| PATCH /alerts/config | 403 | 403 | ✅ |
| GET /suppliers/{id}/alert-recipients | ✅ | ✅ | ✅ |
| PUT /suppliers/{id}/alert-recipients | 403 | ✅ | ✅ |
| DELETE /suppliers/{id}/alert-recipients | 403 | ✅ | ✅ |
