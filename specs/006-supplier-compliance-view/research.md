# Phase 0 Research: Vista de Cumplimiento Anual del Proveedor

## 1. Estrategia de consulta para la cuadrícula

**Decisión**: una sola query SQL que hace JOIN de `supplier_type_document_requirements` → `document_types` → `documents` (filtrado por año y `is_latest=TRUE`), devolviendo todas las filas disponibles de una vez. El servicio Python mapea el resultado a la estructura de celdas.

**Rationale**: la cuadrícula tiene acotado su espacio (≤50 tipos × 12 meses = 600 celdas máximo por proveedor/año). Una query única con el índice `ix_documents_org_supplier_type_period` es suficiente; no justifica múltiples viajes a la DB ni una vista materializada.

**Alternativas consideradas**:
- *N+1 queries (una por tipo de documento)*: descartada; ineficiente y proporcional al número de tipos.
- *Vista materializada / tabla de snapshot*: descartada (YAGNI); añade complejidad operacional sin beneficio medible a esta escala.

---

## 2. Modelo de estados de celda

**Decisión**: siete estados discretos, calculados en el servicio Python al construir la respuesta:

| Estado | Color UI | Condición |
|--------|----------|-----------|
| `validated` | Verde | Documento existe, `is_latest=TRUE`, `status != 'expired'`, `verified=TRUE` |
| `submitted` | Amarillo | Documento existe, `is_latest=TRUE`, `status != 'expired'`, `verified=FALSE` |
| `expired` | Rojo oscuro | Documento existe, `is_latest=TRUE`, `status='expired'` |
| `missing` | Rojo | Período pasado, sin documento (`is_latest=TRUE`) |
| `pending` | Gris claro | Período actual (mes en curso), sin documento aún |
| `future` | Gris | Período futuro (mes aún no iniciado), sin documento |
| `not_required` | Vacío / guión | El mes no corresponde al ciclo de periodicidad del tipo (p. ej., febrero para un tipo anual) |

**Rationale**: distinguir `pending` (mes actual) de `missing` (mes pasado) evita penalizar al usuario por documentos todavía no vencidos. Distinguir `expired` de `missing` (documento existe pero vencido) permite acciones diferentes desde la UI.

**Alternativas consideradas**:
- *Cuatro estados simplificados (ok/warn/fail/future)*: descartada; pierde el matiz "subido sin validar" que es crítico para el flujo del administrador.

---

## 3. Mapeo de periodicidades a meses aplicables

**Decisión**: el servicio calcula qué meses son "períodos de inicio" para cada tipo de documento según su periodicidad efectiva (respetando `periodicity_override` sobre `DocumentType.periodicity`):

| Periodicidad | Meses con período de inicio |
|---|---|
| `monthly` | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 |
| `bimonthly` | 1, 3, 5, 7, 9, 11 (bimestres SAT) |
| `annual` | 1 (enero) |
| `none` | — (sección separada, fuera de la cuadrícula) |

Los meses que no son "período de inicio" para el tipo reciben estado `not_required`.

**Rationale**: `bimonthly` en el contexto REPSE sigue el ciclo bimestral SAT (enero-febrero, marzo-abril, …). Un documento bimestral cubre 2 meses pero se presenta en el primer mes del bimestre.

---

## 4. Renderizado del grid en el frontend

**Decisión**: CSS Grid con Tailwind (`grid-cols-[auto_repeat(12,minmax(0,1fr))]`), sin librería externa. El encabezado de meses es sticky con `sticky top-0`. Cada celda es un componente `ComplianceCell` con Radix `Tooltip` (ya en uso en el proyecto).

**Rationale**: la cuadrícula es sencilla (13 columnas fijas: 1 label + 12 meses), no requiere features avanzados de virtualización ni drag-drop. Tailwind cubre el layout. Radix Tooltip ya está en el bundle del proyecto.

**Alternativas consideradas**:
- *Librería de tabla (TanStack Table)*: descartada; la cuadrícula no necesita sorting/filtering por columna.
- *SVG/Canvas*: descartada; no hay requisito de render de miles de celdas.

---

## 5. Interacción de clic en celda

**Decisión**: las celdas con `document_id` (estados `validated`, `submitted`, `expired`) abren el detalle del documento (reutilizando el mismo token de descarga + modal existente). Las celdas `missing` y `pending` abren el `UploadDialog` preconfigurado con `document_type_id` y `coverage_period_start`.

**Rationale**: reutilizar componentes existentes (`UploadDialog`, `download-token`) evita duplicar lógica y mantiene el comportamiento consistente con la tabla plana actual.

---

## 6. Sección de documentos sin periodicidad (`none`)

**Decisión**: se muestra debajo de la cuadrícula mensual como una lista compacta de tarjetas (una por tipo de documento), cada una con nombre, estado (esfera + texto), fecha de vencimiento si aplica, y acción de subir/ver documento.

**Rationale**: estos documentos no encajan en la cuadrícula de meses; una sección dedicada es más clara que forzarlos en una fila con 12 celdas vacías.
