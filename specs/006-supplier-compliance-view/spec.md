# Feature Specification: Vista de Cumplimiento Anual del Proveedor

**Feature Branch**: `006-supplier-compliance-view`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "Quiero que En la opción de proveedores, Una vez que le hagas clic a uno, Te lleve a un listado de cumplimiento del año en curso. En una cuadrícula vamos a desplegar el tipo de documento y en las columnas vamos a desplegar los meses en los que se debe de cumplir dicha documentación. De tal manera que en esa pantalla puedas visualizar todo el año. y con algún código de color desplegando esferas dentro de cada grilla podamos identificar en qué meses se cumplió, en qué meses no se cumplió, El estatus actual del documento, sí, en efecto, se cumplió y no está validado. Si los documentos no tienen vigencia ver la manera de también poder visualizarlos,"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver cumplimiento anual de un proveedor (Priority: P1)

El administrador de cumplimiento REPSE accede a la lista de proveedores, hace clic en uno y ve inmediatamente la cuadrícula de cumplimiento del año en curso. Cada fila representa un tipo de documento requerido para ese proveedor; cada columna representa un mes del año. Las celdas muestran una esfera de color que indica el estado de la documentación en ese período.

**Why this priority**: Es el núcleo de la feature; sin esta vista no hay valor en ninguna de las demás historias.

**Independent Test**: Se puede testear navegando a un proveedor con documentos registrados y verificando que la cuadrícula muestra 12 columnas de meses y una fila por tipo de documento requerido.

**Acceptance Scenarios**:

1. **Given** el usuario está en la lista de proveedores, **When** hace clic en un proveedor, **Then** se muestra la pantalla de cumplimiento anual con el nombre del proveedor, el año en curso y la cuadrícula completa de 12 meses.
2. **Given** la pantalla de cumplimiento está abierta, **When** se carga, **Then** cada fila muestra el nombre del tipo de documento y cada columna el mes abreviado (Ene, Feb, … Dic).
3. **Given** un proveedor sin ningún tipo de documento asignado, **When** se abre su pantalla de cumplimiento, **Then** se muestra un mensaje indicando que no tiene requisitos de documentación configurados.

---

### User Story 2 - Identificar estado de cumplimiento por color (Priority: P1)

Al ver la cuadrícula, el usuario puede identificar de un vistazo el estado de cada celda gracias a una esfera de color con significado claro. Necesita distinguir cuatro situaciones: cumplido y validado, cumplido pero pendiente de validación, no cumplido (falta el documento) y mes futuro o no requerido.

**Why this priority**: El código de color es la propuesta de valor central de la pantalla; sin él la cuadrícula no es accionable.

**Independent Test**: Se puede testear creando documentos en distintos estados para un mismo proveedor y verificando que cada celda muestra el color correcto.

**Acceptance Scenarios**:

1. **Given** un mes en que el documento fue subido y validado por el administrador, **When** se visualiza la celda, **Then** aparece una esfera **verde**.
2. **Given** un mes en que el documento fue subido pero aún no ha sido revisado/validado, **When** se visualiza la celda, **Then** aparece una esfera **amarilla**.
3. **Given** un mes que ya transcurrió y no se subió ningún documento, **When** se visualiza la celda, **Then** aparece una esfera **roja**.
4. **Given** un mes futuro en que aún no ha llegado la fecha de vencimiento, **When** se visualiza la celda, **Then** aparece una esfera **gris** (pendiente/no aplica aún).
5. **Given** la pantalla cargada, **When** el usuario posiciona el cursor sobre cualquier esfera, **Then** aparece un tooltip con la descripción textual del estado.

---

### User Story 3 - Visualizar documentos sin periodicidad (Priority: P2)

Algunos tipos de documento no tienen vigencia mensual — se presentan una sola vez o tienen una fecha fija de vencimiento (p. ej. acta constitutiva, registro REPSE). El usuario necesita ver también estos documentos en la misma pantalla para tener una vista completa del proveedor.

**Why this priority**: Sin esta historia la vista está incompleta para proveedores con documentos de entrega única, pero la cuadrícula mensual sigue siendo útil de forma independiente.

**Independent Test**: Se puede testear asignando a un proveedor un tipo de documento marcado como "entrega única" y verificando que aparece en la pantalla con su estado pero sin la cuadrícula de meses.

**Acceptance Scenarios**:

1. **Given** un tipo de documento configurado como entrega única o con fecha de vencimiento fija, **When** se muestra la pantalla de cumplimiento, **Then** aparece en una sección separada "Documentos sin periodicidad mensual" con su estado actual (presentado/no presentado/por vencer/vencido).
2. **Given** un documento de entrega única que ya fue subido y validado, **When** se visualiza, **Then** muestra esfera verde y la fecha de vencimiento (si aplica).
3. **Given** un documento de entrega única vencido, **When** se visualiza, **Then** muestra esfera roja y la fecha en que venció.

---

### User Story 4 - Navegar al detalle de un documento desde la cuadrícula (Priority: P3)

Desde cualquier celda de la cuadrícula el usuario puede hacer clic para ver o descargar el documento asociado a ese mes, o para subir el documento faltante directamente.

**Why this priority**: Mejora la fluidez del flujo de trabajo pero no bloquea la lectura del estado de cumplimiento.

**Independent Test**: Se puede testear haciendo clic en una celda verde y verificando que abre el documento, y haciendo clic en una celda roja y verificando que ofrece la opción de subir.

**Acceptance Scenarios**:

1. **Given** una celda verde o amarilla (documento existente), **When** el usuario hace clic en la esfera, **Then** se abre el detalle del documento con opción de descarga.
2. **Given** una celda roja (documento faltante), **When** el usuario hace clic en la esfera, **Then** se abre el diálogo de carga de documento preconfigurado con el tipo de documento y el período correspondiente.

---

### Edge Cases

- ¿Qué pasa si un proveedor tiene más tipos de documentos de los que caben en pantalla sin scroll? → La cuadrícula debe tener scroll vertical; el encabezado de meses permanece fijo.
- ¿Qué pasa si se cambian los requisitos del proveedor a mitad de año? → Los meses anteriores conservan su estado histórico; los nuevos requisitos aplican desde el mes en que se configuraron.
- ¿Qué pasa si el año en curso no tiene datos (proveedor recién dado de alta)? → Se muestra la cuadrícula con todas las esferas en gris para meses pasados y futuras.
- ¿Qué pasa con meses en que un tipo de documento no era requerido para ese proveedor? → La celda muestra un guión o queda vacía, sin esfera.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar, al hacer clic en un proveedor desde la lista, una pantalla dedicada de cumplimiento anual del año en curso.
- **FR-002**: La pantalla DEBE presentar una cuadrícula donde las filas son los tipos de documento requeridos para ese proveedor y las columnas son los doce meses del año.
- **FR-003**: Cada celda de la cuadrícula DEBE mostrar una esfera con código de color: verde (cumplido y validado), amarillo (cumplido sin validar), rojo (no cumplido / mes pasado sin documento), gris (mes futuro o no aplica).
- **FR-004**: El sistema DEBE mostrar una leyenda visible con el significado de cada color en la misma pantalla.
- **FR-005**: Al posicionar el cursor sobre una esfera, DEBE aparecer un tooltip con la descripción textual del estado.
- **FR-006**: Los tipos de documento sin periodicidad mensual DEBEN mostrarse en una sección separada dentro de la misma pantalla, indicando su estado actual y fecha de vencimiento cuando aplique.
- **FR-007**: El encabezado de la columna de meses DEBE permanecer visible al hacer scroll vertical cuando hay muchos tipos de documento.
- **FR-008**: Al hacer clic en una celda con documento existente (verde o amarillo), DEBE abrirse el detalle del documento.
- **FR-009**: Al hacer clic en una celda roja (documento faltante en mes pasado), DEBE ofrecerse la opción de cargar el documento faltante.
- **FR-010**: La pantalla DEBE indicar claramente el nombre del proveedor y el año que se está visualizando.
- **FR-011**: El mes actual DEBE estar visualmente destacado (p. ej. columna resaltada) para facilitar la orientación temporal.

### Key Entities

- **Proveedor**: La empresa proveedora cuyo cumplimiento se visualiza; tiene un tipo de proveedor que determina qué documentos se le exigen.
- **Tipo de documento**: Categoría de documento requerida (p. ej. nómina IMSS, comprobante de pago). Tiene periodicidad (mensual, trimestral, anual, entrega única) y puede tener fecha de vencimiento.
- **Requisito**: Asociación entre un tipo de proveedor y un tipo de documento, que determina en qué meses aplica la obligación.
- **Documento**: Archivo concreto subido por o para un proveedor, vinculado a un período y tipo de documento. Tiene estado: pendiente, validado, rechazado.
- **Celda de cumplimiento**: Estado derivado por período (mes/año) y tipo de documento para un proveedor dado; calculado a partir del documento más reciente aplicable a ese período.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El usuario puede evaluar el estado de cumplimiento completo de un proveedor para todo el año en menos de 30 segundos desde que accede a la pantalla.
- **SC-002**: La pantalla muestra el año completo (12 meses × todos los tipos de documento requeridos) en una sola carga, sin paginación adicional.
- **SC-003**: El código de colores permite identificar correctamente el estado de cualquier celda sin consultar la leyenda en el 90% de los casos tras una primera sesión de uso.
- **SC-004**: Los documentos sin periodicidad mensual son visibles en la misma pantalla, eliminando la necesidad de navegar a otra sección para revisar su estado.
- **SC-005**: El tiempo de carga de la pantalla de cumplimiento anual es perceptiblemente instantáneo para el usuario (menos de 2 segundos en condiciones normales de red interna).

## Assumptions

- El año visualizado por defecto es siempre el año en curso; no se contempla navegación a años anteriores en esta versión.
- La periodicidad de cada tipo de documento ya está configurada en el catálogo (feature 003); esta feature solo la consume.
- El cálculo del estado de cumplimiento por celda es responsabilidad del backend; el frontend solo muestra el resultado.
- Solo los usuarios con rol administrador o supervisor de cumplimiento pueden acceder a esta pantalla; los proveedores no tienen acceso directo.
- Un documento "validado" es aquel que un administrador marcó explícitamente como aprobado; "cumplido sin validar" significa que el archivo existe pero nadie lo ha revisado aún.
- Para tipos de documento con periodicidad trimestral o anual, la celda aplica al primer mes del período y los demás meses del período comparten el mismo estado.
