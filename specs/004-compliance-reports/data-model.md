# Phase 1 Data Model: Reportes Exportables de Cumplimiento

## Entidad nueva: ExportRequest (Solicitud de Exportación)

Tabla: `export_request`. Persiste cada solicitud de exportación, su estado y la referencia al archivo generado. Es la fuente de verdad para el modo asíncrono y la expiración.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `id` | UUID (PK) | Generado al crear. |
| `tenant_id` | FK → tenant | **Obligatorio.** Toda consulta se filtra por este campo (Constitución II). |
| `requested_by` | FK → user | Usuario solicitante. |
| `scope` | enum (`single` / `filtered` / `all`) | Alcance: un proveedor, conjunto filtrado, o todos. |
| `supplier_id` | FK → supplier (nullable) | Requerido solo si `scope = single`. |
| `filters` | JSON | Filtros aplicados (estado, periodo, proveedor, tipo de documento). Vacío para `single`/`all`. |
| `format` | enum (`csv` / `pdf`) | Formato del resumen. |
| `include_originals` | bool | Si `true`, el resultado se empaqueta en ZIP con archivos originales (FR-009). |
| `mode` | enum (`sync` / `async`) | Derivado del umbral; informativo. |
| `status` | enum (`pending` / `generating` / `ready` / `failed` / `expired`) | Máquina de estados (abajo). |
| `file_path` | string (nullable) | Ruta en disco del archivo generado (nombre UUID). Null hasta `ready`. |
| `file_size` | int (nullable) | Tamaño en bytes del archivo generado (FR-008). |
| `error_message` | string (nullable) | Motivo si `status = failed`. |
| `created_at` | datetime (UTC) | Fecha/hora de creación. |
| `expires_at` | datetime (UTC) | `created_at + 24 h` (configurable). Tras vencer → `expired` y borrado del archivo. |
| `completed_at` | datetime (UTC, nullable) | Fecha en que pasó a `ready` o `failed`. |

### Validaciones

- `scope = single` ⇒ `supplier_id` no nulo y perteneciente al tenant.
- `scope = filtered` ⇒ `filters` no vacío.
- `include_originals = true` ⇒ el resultado es un ZIP independientemente de `format` (el resumen va dentro).
- `format` ∈ {csv, pdf}; ZIP no es un `format`, es un empaquetado sobre el resumen.
- Tamaño total del ZIP ≤ límite configurable (default 2 GB) ⇒ si se excede, `status = failed` con `error_message`.

### Máquina de estados

```text
pending ──(worker toma)──> generating ──(éxito)──> ready ──(24 h)──> expired
   │                            │
   │                            └──(error)──> failed
   └──(sync, alcance pequeño)──> generating ──> ready (en la misma request)
```

- **pending**: creada, a la espera de procesamiento (solo modo async).
- **generating**: en proceso (sync inline o tomada por el worker).
- **ready**: archivo disponible para descarga; `file_path`/`file_size` poblados.
- **failed**: error de generación (p. ej. ZIP excede límite); `error_message` poblado.
- **expired**: venció el enlace; archivo borrado, descarga rechazada.

## Entidades reutilizadas (definidas en spec 001 / 003)

- **Proveedor (`supplier`)**: nombre, RFC, estado activo/inactivo, tenant. Origen de las filas del reporte.
- **Documento Cargado (`document`)**: tipo, periodo cubierto, fecha de carga, fecha de vencimiento efectiva, verificado (usuario/fecha), ruta del archivo original. Una fila por (proveedor × tipo esperado).
- **Tipo de Documento de Cumplimiento (`document_type`)**: canónico / personalizado; activo / desactivado / archivado (spec 003). Determina filas "Faltante" y la etiqueta "tipo inactivo / archivado" (FR-011).
- **Usuario (`user`)**: solicitante; su pertenencia al tenant gobierna creación y descarga.
- **Bitácora (`audit`)**: cada exportación registra usuario, fecha/hora, alcance, filtros, formato, resultado y tamaño (FR-008).

## Fila del reporte (proyección, no tabla)

Una fila por (proveedor × tipo de documento esperado), calculada con el mismo motor del módulo `compliance`:

`proveedor, RFC, tipo de documento, origen del tipo (canónico/personalizado), periodo cubierto, estado (vigente/por vencer/vencido/faltante/tipo inactivo), fecha de carga, fecha de vencimiento efectiva, verificado (sí/no, usuario, fecha), enlace interno al archivo`

Reglas:

- Tipos requeridos sin archivo ⇒ estado **Faltante**.
- Tipos desactivados/archivados ⇒ aparecen solo si tienen documentos cargados, etiquetados "tipo inactivo / archivado", **no** cuentan como Faltante (FR-011).
- Proveedor inactivo ⇒ datos históricos, marcado "inactivo" en el encabezado.
- Fechas renderizadas en zona horaria del tenant (FR-012).
