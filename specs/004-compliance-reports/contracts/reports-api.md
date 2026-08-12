# API Contract: Reportes Exportables de Cumplimiento

Prefijo: `/api/reports`. Todos los endpoints requieren sesión válida; el tenant se deriva del usuario autenticado. Ningún endpoint es público (FR-007).

## POST /api/reports/exports

Crea una solicitud de exportación. Decide sync/async según el umbral; en modo síncrono el resultado queda `ready` en la misma respuesta.

**Request body**

```json
{
  "scope": "single | filtered | all",
  "supplier_id": "uuid | null",
  "filters": {
    "status": ["vigente", "por_vencer", "vencido", "faltante"],
    "period_from": "2026-01-01 | null",
    "period_to": "2026-06-30 | null",
    "supplier_ids": ["uuid", "..."],
    "document_type_ids": ["uuid", "..."]
  },
  "format": "csv | pdf",
  "include_originals": false
}
```

Validación:
- `scope = single` ⇒ `supplier_id` requerido (debe pertenecer al tenant; si no, 404).
- `scope = filtered` ⇒ `filters` no vacío.
- `format` ∈ {csv, pdf}.

**Responses**

- `201 Created` (sync, alcance pequeño):
```json
{
  "id": "uuid",
  "status": "ready",
  "mode": "sync",
  "format": "csv",
  "include_originals": false,
  "file_size": 20480,
  "expires_at": "2026-06-15T21:00:00Z",
  "download_url": "/api/reports/exports/{id}/download"
}
```
- `202 Accepted` (async, alcance grande): mismo cuerpo con `status: "pending"`, sin `file_size`, `download_url` presente pero válido solo cuando `status = ready`.
- `400 Bad Request`: payload inválido (combinación de scope/filtros/format).
- `401 Unauthorized`: sin sesión.
- `404 Not Found`: `supplier_id` inexistente o de otro tenant.

## GET /api/reports/exports/{id}

Consulta el estado de una solicitud (usado por el polling del frontend).

**Responses**

- `200 OK`:
```json
{
  "id": "uuid",
  "status": "pending | generating | ready | failed | expired",
  "mode": "sync | async",
  "format": "csv | pdf",
  "include_originals": false,
  "file_size": 20480,
  "error_message": null,
  "created_at": "2026-06-14T21:00:00Z",
  "expires_at": "2026-06-15T21:00:00Z",
  "download_url": "/api/reports/exports/{id}/download"
}
```
- `401 Unauthorized`: sin sesión.
- `404 Not Found`: id inexistente o de otro tenant (no se revela existencia cross-tenant).

## GET /api/reports/exports/{id}/download

Descarga el archivo generado. Verifica sesión y que el usuario pertenezca al tenant emisor (FR-007/FR-010).

**Responses**

- `200 OK`: stream del archivo.
  - CSV ⇒ `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="reporte-cumplimiento.csv"`.
  - PDF ⇒ `application/pdf`.
  - ZIP (`include_originals`) ⇒ `application/zip`.
- `401 Unauthorized`: sin sesión.
- `403 Forbidden`: el solicitante perdió permisos / no pertenece al tenant emisor.
- `404 Not Found`: id inexistente o de otro tenant.
- `410 Gone`: `status = expired` (enlace vencido).
- `409 Conflict`: `status` ∈ {pending, generating} (aún no listo) o `failed`.

## Reglas de auditoría

Cada `POST /exports` (y su resolución final) genera un registro de bitácora con: usuario, fecha/hora, alcance, filtros, formato, resultado (éxito/fallo) y tamaño del archivo (FR-008).

## Casos de prueba de contrato (resumen)

- Crear export sync de un proveedor → `201` con `status: ready` y `download_url`.
- Crear export que excede el umbral → `202` con `status: pending`; polling hasta `ready`.
- Descargar con sesión de **otro tenant** → `404` (no `403`, para no filtrar existencia). *(SC-004 / SC-006)*
- Descargar sin sesión → `401`.
- Descargar export `expired` → `410`.
- `scope = single` sin `supplier_id` → `400`.
