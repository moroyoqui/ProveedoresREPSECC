# Phase 0 Research: Reportes Exportables de Cumplimiento

Resuelve las decisiones técnicas abiertas de la spec 004 antes del diseño. No quedan marcadores NEEDS CLARIFICATION.

## 1. Generación de PDF

- **Decision**: Jinja2 (plantilla HTML/CSS) + **WeasyPrint** para renderizar a PDF.
- **Rationale**: La spec asume "generación de PDF construida sobre una librería de templating" (Assumptions) y exige encabezado de tenant con logo, tabla por proveedor, leyenda de colores, numeración de página (FR-004). HTML+CSS es el camino más directo y mantenible para ese layout; WeasyPrint soporta paginación, encabezados/pies y CSS print. Se integra con el stack Python sin servicios externos.
- **Alternatives considered**:
  - *ReportLab*: muy potente pero el layout es programático (canvas), costoso de mantener para tablas con branding.
  - *fpdf2*: ligero pero limitado para CSS/paginación rica.
  - *wkhtmltopdf*: binario externo sin mantenimiento activo; evita YAGNI pero añade dependencia de proceso.
- **Nota de despliegue**: WeasyPrint requiere libs nativas (Pango/Cairo/GDK-Pixbuf); se añaden al `Dockerfile` del backend. Documentar en quickstart.

## 2. Generación de CSV

- **Decision**: stdlib `csv` con `StreamingResponse` (escritura incremental).
- **Rationale**: Sin dependencias; columnas fijas (FR-003). El streaming evita materializar todo en memoria para alcances medianos síncronos.
- **Alternatives considered**: pandas (overkill, dependencia pesada — viola YAGNI).
- **Formato**: UTF-8 con BOM para compatibilidad con Excel; encabezados en español; separador `,`.

## 3. Empaquetado ZIP con archivos originales

- **Decision**: stdlib `zipfile`; estructura: resumen (CSV/PDF) en la raíz, una carpeta por proveedor, archivos nombrados `{tipo}_{periodo}_{fecha-carga}.{ext}` (FR-009).
- **Rationale**: Sin dependencias; los archivos originales viven en disco local (almacenamiento del proyecto, spec 012). Para alcances grandes el ZIP se genera en modo asíncrono.
- **Límite de tamaño total del ZIP (pendiente en spec, Assumptions)**: **Decision** = límite configurable, por defecto **2 GB** de tamaño total descomprimido; si se excede, la solicitud falla con estado `fallida` y mensaje claro, registrado en bitácora. Evita agotar disco/memoria.
- **Alternatives considered**: tar.gz (menos amigable para usuarios finales en Windows); streaming zip de terceros (innecesario en v1).

## 4. Modo asíncrono y umbral

- **Decision**: Tabla `export_request` como fuente de verdad del estado; un **worker en proceso** (tarea asyncio de larga vida iniciada con la app) consume solicitudes en estado `pendiente`. Umbral por defecto: **50 proveedores o 1000 documentos** (configurable por entorno).
- **Rationale**: Cumple FR-006 (async + notificación + enlace ≥ 24 h) sin introducir Celery/Redis, respetando YAGNI y el despliegue Docker Compose on-prem actual (sin broker). La persistencia en BD hace que las solicitudes sobrevivan reinicios (a diferencia de `BackgroundTasks` en memoria).
- **Alternatives considered**:
  - *FastAPI BackgroundTasks*: se pierden al reiniciar; insuficiente para enlaces de 24 h.
  - *Celery + Redis*: robusto pero añade broker e infraestructura no presente; complejidad no justificada en v1.
  - *APScheduler*: válido, pero un worker asyncio simple sobre la tabla basta y es menos dependencia.
- **Concurrencia**: el worker toma una solicitud a la vez (FIFO) en v1; suficiente para SC-003.

## 5. Notificación in-app

- **Decision**: **Polling de estado** desde el frontend con TanStack Query (`GET /reports/exports/{id}`), mostrando toast/badge cuando el estado pasa a `lista`. Sin infraestructura push (WebSocket/SSE) en v1.
- **Rationale**: No existe un módulo de notificaciones en el backend; el polling cumple "notifica al usuario in-app" con el mínimo de complejidad (YAGNI). Intervalo de polling adaptativo (p. ej. cada 3 s mientras `generando`).
- **Alternatives considered**: SSE/WebSocket (infraestructura adicional innecesaria para v1).

## 6. Almacenamiento y expiración de archivos generados

- **Decision**: Guardar en disco local bajo un directorio de exportaciones, con nombre **UUID** (consistente con spec 012). `export_request.expires_at = created_at + 24 h` (configurable). El worker ejecuta una **limpieza periódica** que borra archivos y marca solicitudes como `expirada` al vencer.
- **Rationale**: Reutiliza el patrón de almacenamiento existente; cumple la suposición de borrado automático al expirar.
- **Alternatives considered**: S3/objeto remoto (fuera del despliegue on-prem actual).

## 7. Descarga protegida por sesión

- **Decision**: `GET /reports/exports/{id}/download` requiere sesión válida; el servicio verifica `export_request.tenant_id == current_user.tenant_id` y que el usuario conserve permisos. Sin tokens públicos ni enlaces firmados (FR-007).
- **Rationale**: La sesión ya autentica al usuario y resuelve el tenant; un token firmado añadiría superficie sin beneficio. Si el solicitante pierde permisos antes de descargar, el chequeo de autorización invalida el acceso (Edge Case del spec).
- **Alternatives considered**: enlaces firmados con expiración (innecesario dado el modelo de sesión).

## 8. Zona horaria y fechas

- **Decision**: `zoneinfo` (stdlib). Zona del tenant configurable; por defecto `America/Mexico_City`. Todas las fechas del reporte se renderizan en esa zona y el encabezado indica explícitamente la zona (FR-012).
- **Rationale**: Sin dependencias; los timestamps se almacenan en UTC y se convierten al renderizar.

## 9. Paridad reporte ↔ pantalla

- **Decision**: El servicio de reportes consume el **mismo cálculo de estado** del módulo `compliance` (spec 001, FR-012) que alimenta la UI, aplicando idénticos filtros. Un test de integración compara el conjunto de filas del export con el del endpoint que usa la pantalla para los mismos filtros (SC-001, FR-005).
- **Rationale**: Garantiza cero discrepancias reutilizando la fuente de verdad en lugar de recalcular.

## Resumen de decisiones

| Tema | Decisión |
|------|----------|
| PDF | Jinja2 + WeasyPrint |
| CSV | stdlib `csv` + StreamingResponse, UTF-8 BOM |
| ZIP | stdlib `zipfile`, límite por defecto 2 GB |
| Async | Tabla `export_request` + worker asyncio en proceso; umbral 50 prov / 1000 docs |
| Notificación | Polling de estado (TanStack Query) |
| Almacenamiento | Disco local, nombre UUID, expiración 24 h + limpieza |
| Descarga | Sesión válida + verificación de tenant; sin enlaces públicos |
| Fechas | `zoneinfo`, default America/Mexico_City |
| Paridad | Reutiliza cálculo del módulo `compliance` |
