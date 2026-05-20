# Contract: Documents

Subida, listado, descarga, sustitución, verificación manual y eliminación de documentos de cumplimiento.

## POST `/api/v1/suppliers/{supplier_id}/documents`

Sube un documento contra un proveedor y tipo.

- **Auth**: requerida. **Roles**: admin, manager.
- **Content-Type**: `multipart/form-data`.
- **Campos**:
  - `file`: archivo binario (≤25 MB, formato en lista permitida: `application/pdf`, `image/png`, `image/jpeg`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).
  - `document_type_id`: int — tipo activo del tenant.
  - `coverage_period_start`: date (`YYYY-MM-DD`). Requerido si la periodicidad del tipo ≠ `none`.
  - `due_date_override`: date (opcional). Si presente, prevalece sobre el cálculo automático y exige `due_date_override_reason`.
  - `due_date_override_reason`: string (max 255). Obligatorio si `due_date_override` ≠ valor calculado.
- **Validaciones**:
  - Tamaño y MIME en lista permitida → si no, `400 unsupported_file`.
  - `document_type_id` activo en el tenant → si no, `409 type_inactive`.
  - `coverage_period_start` consistente con `periodicity` (p. ej. mensual = primer día del mes) → si no, `400 invalid_period`.
- **Respuesta** `201`:
  ```json
  {
    "id": 4521,
    "supplier_id": 12,
    "document_type_id": 1,
    "coverage_period_start": "2026-04-01",
    "coverage_period_end": "2026-04-30",
    "due_date_calculated": "2026-05-31",
    "due_date_effective": "2026-05-31",
    "due_date_override_reason": null,
    "status": "valid",
    "verified": false,
    "verified_by": null,
    "verified_at": null,
    "verified_note": null,
    "version": 1,
    "is_latest": true,
    "file": {
      "name": "opinion-sat-abril.pdf",
      "size_bytes": 423199,
      "mime_type": "application/pdf",
      "sha256": "9af1c3..."
    },
    "ocr": {
      "status": "pending",
      "extracted_rfc": null,
      "extracted_issued_at": null,
      "extracted_valid_until": null
    },
    "audit": {
      "added": {
        "user": { "id": 42, "display_name": "Ana López" },
        "at": "2026-05-02T11:14:00.000-06:00"
      },
      "last_updated": null,
      "validated": null
    }
  }
  ```

- **Notas sobre `audit`** (FR-011a): siempre presente en la respuesta. `added` es inmutable; `last_updated` queda en `null` si no ha habido cambios humanos posteriores; `validated` queda en `null` si nunca se ha verificado. Las acciones del sistema (OCR, recálculo automático de estado) no modifican `last_updated` y se reflejan únicamente en el endpoint de historial.
- **Side effects**:
  - Si ya existía un documento `is_latest=TRUE` para (supplier, type, coverage_period), se archiva (`is_latest=FALSE`) y se incrementa `version` en el nuevo.
  - Si el archivo coincide en `sha256` con otro del mismo tenant, se rechaza `409 duplicate_file` con el `id` existente.
  - Se programa OCR best-effort (sincrónico si ≤3 páginas, asíncrono si más).
  - Se inserta `audit_log` con acción `document.uploaded`.

## GET `/api/v1/documents`

Lista documentos del tenant con filtros. Devuelve la vista global del tenant para la página `/documents`.

- **Auth**: requerida. **Roles**: cualquiera.
- **Query params**:
  - `supplier_id` (opcional): filtrar por proveedor.
  - `document_type_id` (opcional): filtrar por tipo de documento.
  - `status` (opcional): `valid|expiring_soon|expired`.
  - `verified` (opcional, `true|false`): filtrar por estado de verificación.
  - `q` (opcional): búsqueda libre sobre `legal_name` del proveedor.
  - `is_latest` (default `true`).
  - `limit` (default 20), `cursor` (paginación cursor).
- **Respuesta** `200`: lista paginada. Cada item extiende la forma del POST con un campo adicional:
  ```json
  {
    "supplier": { "id": 12, "legal_name": "Servicios Industriales del Norte" }
  }
  ```
  El campo `supplier` siempre está presente en este endpoint (nunca `null`).
- **Notas**: el filtro `q` hace `ILIKE %q%` sobre `suppliers.legal_name`. Multi-tenant: la query ya filtra por `organization_id` vía el tenant filter global.

## GET `/api/v1/documents/{document_id}`

Detalle de un documento.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`: ver POST.
- **Errores**: `404` si no pertenece al tenant.

## POST `/api/v1/documents/{document_id}/download-token`

Emite un token de descarga firmado de corta duración para que el frontend obtenga el archivo.

- **Auth**: requerida. **Roles**: cualquiera.
- **Respuesta** `200`:
  ```json
  { "token": "eyJ...", "expires_at": "2026-05-16T15:30:00.000-06:00" }
  ```
- **Notas**: TTL 5 min. El token incluye `file_id`, `user_id`, `organization_id`, `exp`.

## GET `/api/v1/files/{token}`

Descarga del archivo.

- **Auth**: cookie de sesión + token firmado válidos. La firma + la sesión deben referirse al mismo `organization_id`.
- **Respuesta** `200`: `Content-Type` original, `Content-Disposition: attachment; filename="..."`.
- **Errores**:
  - `401` si la sesión no es válida.
  - `403` `tenant_mismatch` si el token pertenece a otro tenant.
  - `410` `token_expired` si la firma caducó.

## POST `/api/v1/documents/{document_id}/verify`

Marca el documento como "verificado manualmente".

- **Auth**: requerida. **Roles**: admin, manager.
- **Body**:
  ```json
  { "note": "Cotejado con portal del SAT el 2026-05-16" }
  ```
- **Respuesta** `200`: documento con `verified=true`, `verified_by`, `verified_at`, `verified_note`.

## POST `/api/v1/documents/{document_id}/unverify`

Quita la marca de verificación. Registrada en bitácora.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `200`.

## GET `/api/v1/documents/{document_id}/history`

Lista cronológica completa de acciones sobre un documento (sus versiones + sus cambios). Alimenta el tab "Historial" del detalle (FR-011c).

- **Auth**: requerida. **Roles**: cualquiera (incluido `viewer`).
- **Query params**: `cursor`, `limit` (default 50, máx 200), `actor` (`human` | `system` | `all`, default `all`).
- **Respuesta** `200`:
  ```json
  {
    "items": [
      {
        "id": 998877,
        "action": "document.uploaded",
        "actor": { "type": "human", "user": { "id": 42, "display_name": "Ana López" } },
        "summary": "Subió la versión 1 (opinion-sat-abril.pdf)",
        "metadata": { "version": 1, "file_sha256": "9af1c3..." },
        "occurred_at": "2026-05-02T11:14:00.123-06:00"
      },
      {
        "id": 998878,
        "action": "document.ocr_completed",
        "actor": { "type": "system" },
        "summary": "Sistema · OCR completado (RFC detectado)",
        "metadata": { "extracted_rfc": "SIN9001022Y3" },
        "occurred_at": "2026-05-02T11:14:08.501-06:00"
      },
      {
        "id": 999100,
        "action": "document.verified",
        "actor": { "type": "human", "user": { "id": 51, "display_name": "Luis Castro" } },
        "summary": "Marcó como verificado",
        "metadata": { "note": "Cotejado con portal del SAT" },
        "occurred_at": "2026-05-03T09:42:00.000-06:00"
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
  ```
- **Errores**: `404` si el documento no pertenece al tenant.

## DELETE `/api/v1/documents/{document_id}`

Elimina un documento dentro de la **ventana de gracia** (configurable; default 24 h tras la subida). Pasada la ventana, se rechaza y la única vía es sustituir con una nueva versión.

- **Auth**: requerida. **Roles**: admin.
- **Respuesta** `204` si fue eliminado (archivo físico borrado, fila soft-delete con `deleted_at`).
- **Errores**: `409 delete_window_expired`.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /documents, /documents/{id} | ✅ | ✅ | ✅ |
| GET /documents/{id}/history | ✅ | ✅ | ✅ |
| POST /suppliers/{id}/documents | 403 | ✅ | ✅ |
| POST /documents/{id}/download-token | ✅ | ✅ | ✅ |
| GET /files/{token} | ✅ | ✅ | ✅ |
| POST /documents/{id}/verify | 403 | ✅ | ✅ |
| POST /documents/{id}/unverify | 403 | 403 | ✅ |
| DELETE /documents/{id} | 403 | 403 | ✅ |
