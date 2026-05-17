# Contract: Audit Log

Consulta de la bitácora del tenant. Append-only en el backend; este endpoint es lectura solamente.

## GET `/api/v1/audit-log`

Lista eventos de auditoría del tenant.

- **Auth**: requerida. **Roles**: admin, manager.
- **Query params**:
  - `actor_user_id` (opcional).
  - `entity_type` (opcional, p. ej. `supplier`, `document`).
  - `entity_id` (opcional).
  - `action` (opcional, p. ej. `document.uploaded`).
  - `since`, `until` (timestamps ISO).
  - `cursor`, `limit` (default 50, máx 200).
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 998877,
        "actor": { "id": 42, "display_name": "Ana López", "email": "ana@empresa.mx" },
        "action": "document.uploaded",
        "entity_type": "document",
        "entity_id": 4521,
        "metadata": {
          "supplier_id": 12,
          "document_type_id": 1,
          "file_sha256": "9af1c3...",
          "ip": "201.x.x.x",
          "user_agent": "Mozilla/5.0 ..."
        },
        "created_at": "2026-05-02T11:14:00.123-06:00"
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
  ```

## Acciones registradas (lista mínima v1)

| `action` | Cuándo se emite | Metadata clave |
|----------|-----------------|----------------|
| `auth.login` | Tras callback OIDC exitoso | provider, ip, user_agent |
| `auth.logout` | Logout manual | — |
| `organization.updated` | PATCH /organization | campos cambiados (prev/new) |
| `user.created` | POST /users | role |
| `user.role_changed` | PATCH /users/{id} (role) | prev_role, new_role |
| `user.disabled` | DELETE /users/{id} | — |
| `supplier.created` | POST /suppliers | rfc, legal_name |
| `supplier.updated` | PATCH /suppliers/{id} | campos cambiados |
| `supplier.deactivated` | DELETE /suppliers/{id} | — |
| `supplier.reactivated` | POST /suppliers/{id}/reactivate | — |
| `document.uploaded` | POST /suppliers/{id}/documents | document_type_id, coverage_period_start, sha256 |
| `document.due_date_overridden` | Subida con `due_date_override` ≠ calculado | prev_calculated, override, reason |
| `document.verified` | POST /documents/{id}/verify | note |
| `document.unverified` | POST /documents/{id}/unverify | — |
| `document.deleted` | DELETE /documents/{id} | reason |

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /audit-log | 403 | ✅ | ✅ |

**Nota**: `viewer` queda fuera de la bitácora por defecto porque puede contener metadatos sensibles (RFCs, hashes, IPs). Si en el futuro un cliente lo solicita, se puede abrir con un sub-rol.
