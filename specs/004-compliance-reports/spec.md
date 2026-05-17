# Feature Specification: Reportes Exportables de Cumplimiento

**Feature Branch**: `004-compliance-reports`

**Created**: 2026-05-16

**Status**: Draft

**Depends on**: [`001-repse-compliance-tracker`](../001-repse-compliance-tracker/spec.md) (entidades `Proveedor`, `Documento Cargado`, `Tipo de Documento de Cumplimiento`, estado calculado en FR-012). Opcionalmente complementa el spec [`003-document-catalog-admin`](../003-document-catalog-admin/spec.md) cuando el reporte respeta tipos desactivados/archivados.

## Scope

Permite exportar el estado de cumplimiento de uno o varios proveedores a un archivo descargable, para fines de auditoría interna, entrega a un cliente final o evidencia frente a inspecciones laborales. Cubre:

- Exportación de **CSV** (datos tabulares) y **PDF** (reporte presentable) para uno, varios o todos los proveedores del tenant.
- Filtros por estado, periodo, proveedor y tipo de documento.
- Empaquetado opcional con los **archivos originales** en un ZIP.
- Auditoría del propio acto de exportar.

Fuera de alcance: generación programada (recurrente) de reportes, envío automático por correo, integración con Drive/SharePoint.

## Clarifications

Aplica el bloque de **clarificaciones globales** del spec 001 (sesión 2026-05-16). Ver [`001-repse-compliance-tracker/spec.md#clarifications`](../001-repse-compliance-tracker/spec.md#clarifications). Específicamente: solo el cliente contratante consume reportes (no hay portal de proveedor); los datos respetan el aislamiento multi-tenant.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exportar reporte de cumplimiento de un proveedor (Priority: P1)

Un usuario abre el detalle de un proveedor y solicita exportar su reporte de cumplimiento. Recibe un archivo (CSV o PDF, a elegir) con una fila por documento esperado: tipo, periodo, estado, fecha de carga, fecha de vencimiento efectiva, marca de verificación y enlace interno al archivo.

**Why this priority**: Es el caso 80/20; cubre la necesidad de "tengo que mostrarle a alguien que este proveedor está cumpliendo" sin pedirle que entre al sistema.

**Independent Test**: Generar el CSV de un proveedor con 5 documentos en estados mixtos; verificar que el archivo tiene 5 filas y los valores coinciden con la pantalla.

**Acceptance Scenarios**:

1. **Given** un proveedor con documentos en distintos estados, **When** el usuario solicita exportar en formato CSV, **Then** recibe un archivo con una fila por documento esperado (incluyendo "Faltante" para los requeridos sin archivo) con columnas: proveedor, RFC, tipo, periodo cubierto, estado, fecha de carga, fecha de vencimiento efectiva, verificado (sí/no, usuario, fecha), enlace al archivo.
2. **Given** el mismo proveedor, **When** el usuario solicita exportar en formato PDF, **Then** recibe un archivo con encabezado del tenant, fecha de generación, datos del proveedor y la misma información tabular, con leyendas legibles para impresión.
3. **Given** un proveedor sin documentos cargados, **When** se exporta, **Then** el archivo se genera mostrando "Faltante" para cada tipo activo requerido por el tenant, sin error.

---

### User Story 2 - Exportar reporte agregado de múltiples proveedores (Priority: P2)

Un usuario filtra el listado de proveedores (por estado de cumplimiento, etiqueta, etc.) y exporta un reporte que consolida a todos los proveedores filtrados, una fila por (proveedor × documento), útil para revisiones masivas o entregas trimestrales.

**Why this priority**: Es el caso de uso de auditoría real cuando hay decenas o cientos de proveedores. No es indispensable para v1 pero entrega mucho valor a clientes medianos/grandes.

**Independent Test**: Filtrar 10 proveedores con estado "Vencido" o "Por vencer" y exportar; verificar que el archivo contiene una fila por (proveedor × documento) y refleja los filtros aplicados.

**Acceptance Scenarios**:

1. **Given** 10 proveedores en el listado filtrado, **When** se solicita la exportación, **Then** el archivo incluye únicamente esos 10 proveedores y respeta los filtros aplicados al listado.
2. **Given** un volumen de proveedores que excede el procesamiento síncrono razonable (umbral configurable, por defecto 50 proveedores), **When** se solicita la exportación, **Then** el sistema procesa la solicitud asíncronamente y notifica al usuario in-app cuando el archivo está listo para descarga, con un enlace válido por al menos 24 horas.

---

### User Story 3 - Empaquetar reporte con archivos originales (Priority: P3)

Un usuario solicita, además del CSV/PDF, descargar un ZIP con los archivos originales de cada documento referenciado, organizados por proveedor y tipo, para entregar a un auditor externo.

**Why this priority**: Es deseable para auditorías formales, pero los reportes simples ya cubren la mayoría de los casos. Solo lo usaría un subconjunto de clientes.

**Independent Test**: Generar el ZIP con un proveedor de 5 documentos; verificar que el archivo contiene los 5 PDFs originales + el CSV/PDF resumen, en una estructura clara.

**Acceptance Scenarios**:

1. **Given** un proveedor con 5 documentos cargados, **When** el usuario solicita el reporte con archivos originales en ZIP, **Then** recibe un ZIP con: (a) un resumen CSV o PDF en la raíz, (b) una carpeta por proveedor, (c) los archivos originales adentro con nombre que incluya tipo y periodo.
2. **Given** un proveedor con un tipo activo "Faltante", **When** se genera el ZIP, **Then** ese tipo aparece en el resumen como "Faltante" y la carpeta del proveedor no contiene archivo para él (sin generar errores).

---

### Edge Cases

- ¿Qué pasa si el reporte se solicita para un proveedor inactivo? El reporte se genera con sus datos históricos, marcando claramente al proveedor como "inactivo" en el encabezado.
- ¿Qué pasa con tipos desactivados o archivados (spec 003)? El reporte los muestra solo si existían documentos cargados sobre ellos, etiquetados como "tipo inactivo / archivado", y no los cuenta como "Faltante".
- ¿Qué pasa si el volumen es muy grande (cientos de proveedores)? La exportación cambia a modo asíncrono con notificación in-app cuando esté lista (FR-006).
- ¿Quién puede ver/exportar el reporte? Todos los roles del tenant excepto explícitamente restringidos; cada exportación queda en bitácora con usuario, fecha y filtros aplicados.
- ¿Qué pasa si el usuario que generó el reporte deja de tener permisos antes de descargarlo? El enlace de descarga es invalidado.
- ¿El enlace de descarga es accesible sin sesión? No. Cualquier descarga requiere sesión válida y verifica que el usuario pertenece al tenant emisor (FR-019 del spec 001).
- ¿Qué pasa con la zona horaria al renderizar fechas? Se usa la zona horaria del tenant (por defecto Ciudad de México) y se indica explícitamente en el encabezado del reporte.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ofrecer exportación del reporte de cumplimiento en al menos dos formatos: **CSV** (para análisis de datos) y **PDF** (para presentación / impresión).
- **FR-002**: La exportación DEBE soportar tres alcances: (a) un solo proveedor desde su detalle, (b) un conjunto de proveedores resultantes de aplicar filtros al listado, (c) todos los proveedores del tenant.
- **FR-003**: El CSV DEBE incluir al menos las columnas: proveedor, RFC, tipo de documento, origen del tipo (canónico / personalizado), periodo cubierto, estado (vigente / por vencer / vencido / faltante / tipo inactivo), fecha de carga, fecha de vencimiento efectiva, verificado (sí/no, usuario, fecha), enlace interno al archivo.
- **FR-004**: El PDF DEBE incluir: encabezado del tenant (nombre, logo si está configurado), fecha y hora de generación con zona horaria, filtros aplicados, datos del proveedor (o lista de proveedores), tabla de documentos por proveedor, leyenda de colores/estados, número de página y total.
- **FR-005**: El reporte DEBE reflejar exactamente lo visible en la interfaz para los mismos filtros aplicados al momento de generarse; cero discrepancias.
- **FR-006**: Si el alcance excede un umbral configurable (por defecto 50 proveedores o 1000 documentos), la generación DEBE ejecutarse asíncronamente y notificar al usuario in-app cuando el archivo esté listo. El enlace de descarga DEBE estar disponible al menos 24 horas.
- **FR-007**: El acceso al archivo descargable DEBE requerir sesión válida del usuario que pertenece al tenant emisor; los enlaces NO DEBEN ser públicos.
- **FR-008**: Cada solicitud de exportación DEBE registrarse en la bitácora con: usuario, fecha/hora, alcance, filtros aplicados, formato, resultado (éxito/fallo) y tamaño del archivo generado.
- **FR-009**: El sistema DEBE permitir, opcionalmente, **empaquetar los archivos originales en un ZIP** junto con el resumen (CSV o PDF). La estructura del ZIP: resumen en la raíz; una carpeta por proveedor; nombre de archivo dentro de la carpeta = `{tipo}_{periodo}_{fecha-carga}.{ext}`.
- **FR-010**: La exportación DEBE respetar el aislamiento multi-tenant: ningún reporte puede contener datos de proveedores que no pertenecen al tenant del usuario que lo solicita.
- **FR-011**: Los tipos de documento desactivados o archivados (spec 003) DEBEN aparecer en el reporte solo si tienen documentos cargados, etiquetados como "tipo inactivo / archivado", y NO DEBEN contar como "Faltante".
- **FR-012**: Las fechas en el reporte DEBEN renderizarse en la zona horaria del tenant (configurable; por defecto Ciudad de México), e indicar explícitamente la zona en el encabezado.

### Key Entities

- **Solicitud de Exportación**: Atributos: id, tenant, usuario solicitante, alcance (proveedor único / filtrado / completo), filtros aplicados, formato (CSV / PDF / ZIP), modo (síncrono / asíncrono), estado (pendiente / generando / lista / fallida / expirada), fecha de creación, fecha de expiración del enlace, referencia al archivo generado, tamaño.
- Las entidades `Proveedor`, `Documento Cargado`, `Tipo de Documento de Cumplimiento`, `Usuario`, `Bitácora` están definidas en el spec 001 y son reutilizadas aquí.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El reporte exportado coincide al 100% con lo mostrado en pantalla para el mismo conjunto de proveedores y filtros, validado en pruebas automatizadas.
- **SC-002**: Para alcances pequeños (≤ 10 proveedores), el archivo se genera y descarga en menos de 5 segundos.
- **SC-003**: Para alcances grandes (50+ proveedores), la exportación asíncrona completa en menos de 5 minutos para 90% de los casos en condiciones normales.
- **SC-004**: Cero fugas multi-tenant: ningún reporte puede contener datos de tenants distintos al del solicitante, validado en pruebas automatizadas.
- **SC-005**: Cada exportación queda en la bitácora con todos los campos requeridos (FR-008); 0% de exportaciones sin registro.
- **SC-006**: Los enlaces de descarga generados NO son accesibles sin sesión válida del tenant: 0% de descargas exitosas con sesión inválida o de otro tenant en pruebas.

## Assumptions

- Cualquier usuario del tenant puede generar reportes; no se diferencia por rol en v1. Si se requiere restricción por rol, se ajusta en una fase posterior.
- La generación de PDF se construye sobre una librería de templating; el branding se limita al nombre/logo del tenant en v1.
- El almacenamiento temporal de archivos exportados se elimina automáticamente al cumplirse el plazo de expiración del enlace (24 h por defecto).
- En v1 no hay programación recurrente (cron) de reportes ni envío automático por correo; eso queda para una fase posterior.
- Para alcances muy grandes (todos los proveedores con archivos originales en ZIP), aplica el modo asíncrono y un límite de tamaño total del ZIP a definir en `/speckit-plan`.
