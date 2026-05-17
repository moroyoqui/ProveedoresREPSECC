# Feature Specification: Tablero de Control de Cumplimiento

**Feature Branch**: `005-compliance-dashboard`

**Created**: 2026-05-16

**Status**: Draft

**Input**: User description: "quiero que definas un spec acerca de un tablero de control del cumplimiento de los proveedores, debera filtrar por año, deberiamos de poder ver por tipo de documento, desglose en pastel de los que estan en cumplimiento y los que estan vencidos, etc"

**Depends on**: [`001-repse-compliance-tracker`](../001-repse-compliance-tracker/spec.md) (entidades `Proveedor`, `Documento Cargado`, `Tipo de Documento de Cumplimiento` y estado calculado en FR-012). Complementa [`003-document-catalog-admin`](../003-document-catalog-admin/spec.md) al respetar tipos activos/desactivados.

## Scope

Vista analítica de **una sola pantalla** que permite a un usuario del tenant ver el estado de cumplimiento agregado de **todos sus proveedores** con cortes por año, tipo de proveedor, tipo de documento y estado, complementando el indicador por proveedor del spec 001 (que es a nivel detalle). Cubre:

- Filtros por **año**, **tipo de proveedor**, tipo de documento, proveedor y estado.
- **Gráfico de pastel** con el desglose por estado (vigente / por vencer / vencido / faltante).
- **Gráfico de barras** del cumplimiento por tipo de documento.
- **KPIs** numéricos: cumplimiento global, proveedores en riesgo, documentos próximos a vencer.
- **Drill-down**: hacer click en una porción del pastel o una barra lleva al listado de proveedores/documentos correspondiente.

Fuera de alcance: tendencias históricas mes a mes (queda para v2), comparación entre tenants, gráficos personalizables por el usuario, dashboards configurables por widget.

## Clarifications

Aplica el bloque de **clarificaciones globales** del spec 001 (sesión 2026-05-16). Ver [`001-repse-compliance-tracker/spec.md#clarifications`](../001-repse-compliance-tracker/spec.md#clarifications). En particular:

- El tablero respeta el aislamiento multi-tenant: solo muestra datos del tenant del usuario logueado.
- Estados de documento son los definidos en spec 001 FR-012: vigente / por vencer / vencido / faltante. Adicionalmente el tablero reconoce "tipo inactivo" cuando corresponde, según FR-011 del spec 003/004.
- **Documentos requeridos por proveedor** = derivados del `SupplierType` del proveedor (spec 001 FR-012b). El KPI "proveedor en riesgo", el cálculo de "Faltante" y el cumplimiento agregado se evalúan SOLO contra los requisitos del tipo del proveedor (no contra el catálogo del tenant entero).

### Session 2026-05-16

- Q: ¿Cómo se define "Proveedor en riesgo" para el KPI principal del tablero? → A: Proveedor **activo** que tiene al menos un documento en estado **"Vencido" o "Faltante"** sobre un **tipo activo** del catálogo del tenant. "Faltante" cuenta como riesgo porque representa el mismo incumplimiento legal que "Vencido".
- Q: ¿Qué frescura de datos espera el usuario al abrir el tablero o cambiar filtros? → A: Tiempo **casi-real**: cada apertura o cambio de filtro recalcula desde la fuente. Cache de **hasta 60 segundos** a nivel servidor para proteger performance ante refrescos repetidos; el cache DEBE invalidarse automáticamente al subir, editar o eliminar un documento del tenant.
- Q: ¿Se incluye el filtro por "etiquetas" de proveedor en este spec? → A: No. Las etiquetas no están definidas en el modelo de datos actual (spec 001) y se sacan de este spec para no introducir un FR fantasma. Si se priorizan en el futuro, se crearán como nuevo spec independiente y se integrarán al tablero con un cambio aditivo pequeño.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vista global del cumplimiento del año en curso (Priority: P1)

Al abrir el tablero, un usuario ve de inmediato el estado de cumplimiento agregado del tenant para el año en curso, sin necesidad de aplicar filtros: un gráfico de pastel con el desglose por estado, KPIs principales y un gráfico de barras del cumplimiento por tipo de documento. Esto le permite contestar en segundos "¿qué tan bien estamos en cumplimiento ahora mismo?".

**Why this priority**: Es el caso 80/20 del tablero; sin esto el feature no entrega valor. La vista por defecto debe ser comprensible sin tocar nada.

**Independent Test**: Cargar el tablero como usuario de un tenant con al menos 10 proveedores con documentos en distintos estados; verificar que el pastel, las barras y los KPIs cargan sin filtros y reflejan los datos del año en curso.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado de un tenant con proveedores y documentos, **When** abre el tablero por primera vez, **Then** la vista por defecto muestra los datos del año calendario en curso con: (a) pastel de estados, (b) barras por tipo de documento, (c) KPIs (cumplimiento global %, proveedores activos, proveedores en riesgo, documentos por vencer en 30 días).
2. **Given** la vista por defecto, **When** el usuario revisa el pastel, **Then** las cuatro porciones (vigente, por vencer, vencido, faltante) suman exactamente 100% y los conteos exhibidos coinciden con la base de datos al momento de la consulta.
3. **Given** un tenant sin proveedores aún, **When** el usuario abre el tablero, **Then** se muestra un estado vacío informativo con una llamada a la acción para registrar el primer proveedor, sin gráficos vacíos confusos.

---

### User Story 2 - Filtrar por año (Priority: P1)

El usuario puede cambiar el filtro de año (con un selector que ofrece los últimos N años con datos, por defecto los últimos 5) y todo el tablero se recalcula para mostrar el estado de cumplimiento de los documentos cubriendo ese año.

**Why this priority**: El usuario lo pidió explícitamente y es indispensable para reportes anuales/auditorías retrospectivas.

**Independent Test**: Cambiar el año del selector al año anterior; verificar que el pastel, las barras y los KPIs reflejan los documentos cuyo periodo cubierto cae en ese año.

**Acceptance Scenarios**:

1. **Given** un tenant con documentos en 2024 y 2025, **When** el usuario selecciona "2024" en el filtro de año, **Then** todos los componentes del tablero se actualizan para mostrar únicamente documentos con periodo cubierto en 2024 (y "faltante" para los tipos requeridos que no se cubrieron ese año).
2. **Given** el filtro en un año futuro sin datos, **When** se aplica, **Then** se muestra estado vacío explicando que no hay datos para ese periodo.
3. **Given** el filtro en un año pasado, **When** se aplica, **Then** los estados "por vencer" se evalúan respecto al cierre del año seleccionado (no a la fecha de hoy), de modo que el tablero refleja el estado fotográfico de ese año.

---

### User Story 3 - Filtrar por tipo de documento y otros cortes (Priority: P2)

Además del año, el usuario puede aplicar filtros adicionales: tipo de documento (uno o varios), proveedor (uno o varios), estado (uno o varios), y etiquetas si están configuradas en el tenant. Todos los gráficos y KPIs respetan los filtros aplicados.

**Why this priority**: Convierte el tablero en herramienta de diagnóstico ("¿qué pasó con la opinión SAT de mis proveedores de construcción?"). Importante pero el tablero ya entrega valor sin esto.

**Independent Test**: Filtrar por tipo "Opinión SAT" + estado "Vencido" y verificar que los componentes muestran solo proveedores con opinión SAT vencida.

**Acceptance Scenarios**:

1. **Given** el filtro en tipo de documento "Opinión SAT", **When** se aplica, **Then** los componentes muestran únicamente documentos de ese tipo y el pastel mantiene la suma 100% relativa a ese subconjunto.
2. **Given** múltiples filtros aplicados (año + tipo + estado), **When** el usuario presiona "limpiar filtros", **Then** la vista regresa a la configuración por defecto (año en curso, sin otros filtros).
3. **Given** filtros aplicados, **When** el usuario refresca la página o comparte la URL, **Then** los filtros se reconstruyen tal cual estaban (filtros codificados en la URL).

---

### User Story 4 - Drill-down desde el tablero al listado (Priority: P2)

Al hacer click sobre una porción del pastel, una barra del gráfico o un KPI, el usuario navega al listado de proveedores/documentos correspondiente con los filtros del tablero ya aplicados, sin tener que reconstruirlos manualmente.

**Why this priority**: Eleva el tablero de "diagnóstico visual" a "punto de partida operativo". Sin drill-down, el usuario tendría que ir al listado y refiltrar a mano.

**Independent Test**: Click sobre la porción "Vencido" del pastel y verificar que se abre el listado de documentos en estado "Vencido" con el mismo año/tipo aplicado en el tablero.

**Acceptance Scenarios**:

1. **Given** el tablero con filtros activos, **When** el usuario hace click en la porción "Vencido" del pastel, **Then** navega al listado de documentos filtrado por (año del tablero) + (cualquier otro filtro activo) + estado "Vencido".
2. **Given** el gráfico de barras por tipo de documento, **When** el usuario hace click en la barra de "Opinión IMSS", **Then** navega al listado de proveedores con la dimensión "Opinión IMSS" agregada al filtro.
3. **Given** un KPI "Documentos por vencer en 30 días", **When** el usuario lo presiona, **Then** llega al listado de esos documentos.

---

### Edge Cases

- ¿Qué pasa si el tenant tiene cero proveedores? Estado vacío con llamada a la acción ("Registra tu primer proveedor"), sin gráficos vacíos.
- ¿Qué pasa con tipos desactivados o archivados (spec 003)? El tablero NO los incluye en "Faltante", pero sí muestra los documentos cargados sobre ellos etiquetados con "tipo inactivo" si hay datos en el año filtrado.
- ¿Cómo se calcula "por vencer" cuando el filtro de año es un año pasado? Se calcula respecto al **cierre del año seleccionado** (31 de diciembre 23:59 hora del tenant), no respecto a hoy, para que el tablero sea consistente histórica y prospectivamente.
- ¿Qué pasa si dos proveedores tienen el mismo tipo de documento en distintos estados para el mismo periodo? Cada documento cuenta como una unidad independiente en los gráficos.
- ¿Qué pasa si un usuario tiene rol de solo consulta? Ve todo el tablero pero el drill-down lleva a un listado de solo lectura sin acciones de edición/carga.
- ¿Qué pasa si la cantidad de proveedores es muy grande (>500)? El tablero usa agregación en servidor; los conteos se muestran agregados sin demoras superiores a las metas de performance.
- ¿Qué pasa si el usuario tiene un huso horario distinto al del tenant? Las fechas en el tablero se renderizan en la zona horaria del tenant (configurable; por defecto Ciudad de México) y se indica explícitamente en la UI.
- ¿Qué pasa si un proveedor está inactivo? Por defecto se excluye del tablero; un filtro adicional "incluir proveedores inactivos" lo incorpora cuando el usuario lo necesita para auditorías.

## Requirements *(mandatory)*

### Functional Requirements

**Vista por defecto y composición**

- **FR-001**: El tablero DEBE estar accesible para los tres roles del tenant (administrador, gestor, consulta) y aislado por tenant (FR-003 del spec 001).
- **FR-002**: La vista por defecto, sin filtros aplicados, DEBE mostrar: año = año calendario en curso, alcance = todos los proveedores activos del tenant, todos los tipos activos del catálogo.
- **FR-003**: El tablero DEBE contener al menos cuatro componentes visibles sin desplazamiento en pantalla de escritorio: (a) gráfico de **pastel** del desglose por estado de cumplimiento, (b) gráfico de **barras** del cumplimiento por tipo de documento, (c) tira de **KPIs** numéricos, (d) tabla resumen por proveedor con su porcentaje de cumplimiento.
- **FR-004**: Los KPIs DEBEN incluir como mínimo: porcentaje de cumplimiento global, número de proveedores activos, **número de proveedores en riesgo** (definido en FR-004a), número de documentos por vencer en los próximos 30 días.
- **FR-004a**: Un **proveedor en riesgo** es un proveedor en estado **activo** que tiene al menos un documento en estado **"Vencido" o "Faltante"** entre los **requisitos exigidos por su `SupplierType`** (asociaciones `SupplierTypeDocumentRequirement` activas que apuntan a `DocumentType` activos). Proveedores inactivos, tipos de documento desactivados/archivados y requisitos retirados no contribuyen al conteo de riesgo. Esta definición DEBE usarse consistentemente en el KPI, en el drill-down (FR-017) y en las pruebas automatizadas.

**Filtros**

- **FR-005**: El tablero DEBE ofrecer un filtro por **año** mediante un selector que liste los años con al menos un documento cargado en el tenant (más el año en curso), con un máximo razonable de 10 años hacia atrás.
- **FR-006**: El tablero DEBE ofrecer filtros adicionales: **tipo de proveedor** (multi-selección, incluye "Sin clasificar"), **tipo de documento** (multi-selección), **proveedor** (multi-selección con búsqueda por nombre o RFC) y **estado** (multi-selección de los cuatro estados base). El filtro por etiquetas queda explícitamente fuera de alcance hasta que el modelo de datos incorpore esa capacidad.
- **FR-007**: Todos los componentes del tablero DEBEN respetar los filtros aplicados y mostrar conteos consistentes entre sí. La suma del pastel siempre representa el 100% del subconjunto filtrado.
- **FR-008**: Los filtros DEBEN codificarse en la URL, de manera que recargar la página o compartir el enlace reconstruya exactamente la misma vista.
- **FR-009**: Un botón "Limpiar filtros" DEBE regresar la vista al estado por defecto (año en curso, sin otros filtros) en una sola acción.

**Cálculo del estado y semántica del año**

- **FR-010**: El **estado** de cada documento se determina con las reglas de FR-012 del spec 001 (vigente / por vencer / vencido / faltante).
- **FR-011**: Cuando el filtro de año es **el año en curso**, los estados se evalúan respecto a **hoy** (zona horaria del tenant).
- **FR-012**: Cuando el filtro de año es un **año pasado**, los estados se evalúan respecto al **cierre del 31 de diciembre 23:59** de ese año (zona horaria del tenant), de modo que el tablero refleje un estado fotográfico de cierre de año, no el estado actual proyectado al pasado.
- **FR-013**: El alcance del año cubre los documentos cuyo **periodo cubierto** intersecta el año seleccionado (no la fecha de carga). Para documentos "sin vigencia", se incluyen únicamente si su fecha de carga cae dentro del año seleccionado.
- **FR-014**: Los tipos de documento **desactivados o archivados** dentro del tenant NO DEBEN contar como "Faltante" en ningún componente; los documentos cargados sobre tipos inactivos sí aparecen, etiquetados como tales.

**Drill-down e interacción**

- **FR-015**: Hacer click en una porción del pastel DEBE llevar al listado de documentos filtrado por (filtros activos del tablero) + estado correspondiente.
- **FR-016**: Hacer click en una barra del gráfico por tipo de documento DEBE llevar al listado de documentos filtrado por (filtros activos del tablero) + ese tipo.
- **FR-017**: Hacer click en un KPI cuando representa un subconjunto navegable (p. ej. "Proveedores en riesgo", "Documentos por vencer en 30 días") DEBE llevar al listado correspondiente con los filtros equivalentes aplicados.

**Estados vacíos y errores**

- **FR-018**: Cuando un filtro produce un conjunto vacío, los gráficos DEBEN reemplazarse por un mensaje informativo que indique el filtro vacío y sugiera limpiarlo o ajustarlo, en lugar de mostrar gráficos sin datos.
- **FR-019**: Cuando un tenant aún no tiene proveedores ni documentos, el tablero DEBE mostrar un estado de bienvenida con llamada a la acción.

**Performance y consistencia**

- **FR-020**: Las consultas que alimentan el tablero DEBEN agregarse en servidor (no transferir registros uno por uno al cliente para sumar) y devolver resultados consistentes con la vista de detalle por proveedor; cero discrepancias entre tablero y detalle del proveedor para los mismos filtros.
- **FR-021**: El tablero DEBE operar en **frescura casi-real**: cada apertura o cambio de filtro recalcula desde la fuente de datos del tenant. Se permite un cache en servidor de hasta **60 segundos** por combinación (tenant, filtros, usuario) para proteger performance ante refrescos repetidos.
- **FR-021a**: El cache del tablero DEBE invalidarse automáticamente para el tenant correspondiente al ocurrir cualquiera de los siguientes eventos: carga, edición o eliminación de un documento; cambio en el catálogo del tenant (activar/desactivar/archivar tipo); alta/baja/reactivación de un proveedor; cambio de configuración que afecte el cálculo de estado (umbral "por vencer", overrides de vencimiento).
- **FR-021b**: El tablero DEBE mostrar un indicador discreto con la hora local del último cálculo (zona horaria del tenant), de modo que el usuario sepa si está viendo datos recientes o procedentes del cache.

### Key Entities

Este spec no introduce entidades nuevas; reutiliza `Organización (Tenant)`, `Proveedor`, `Tipo de Documento de Cumplimiento`, `Documento Cargado`, `Usuario` y `Bitácora` definidos en el spec 001. Opcionalmente puede introducir un objeto en memoria/cache:

- **Vista Agregada del Tablero**: Snapshot transitorio del conteo por (estado × tipo × proveedor) para los filtros aplicados, calculado bajo demanda y opcionalmente cacheado a corto plazo. Atributos: filtros, conteos por categoría, momento de cálculo. No se persiste permanentemente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El tablero carga la vista por defecto en menos de **2 segundos** percibidos por el usuario en tenants con hasta 500 proveedores y 50 000 documentos.
- **SC-002**: Aplicar o cambiar un filtro recalcula el tablero en menos de **1.5 segundos** en el mismo rango de tamaño.
- **SC-003**: Cero discrepancias entre los conteos del tablero y el detalle por proveedor para los mismos filtros, validado en pruebas automatizadas que comparan ambos endpoints sobre datos sembrados.
- **SC-004**: Un usuario que entra por primera vez al tablero puede identificar en menos de **30 segundos** "cuántos proveedores tienen documentos vencidos este año", medido en pruebas de usabilidad con al menos 5 participantes.
- **SC-005**: 100% de las interacciones de drill-down llevan al listado con los filtros del tablero aplicados correctamente.
- **SC-006**: Cero fugas multi-tenant: ningún tablero muestra datos de otro tenant ni siquiera en agregados o conteos, validado en pruebas automatizadas.
- **SC-007**: La suma de las porciones del pastel siempre es exactamente 100% (con redondeo controlado para que no se vea "99% / 101%") en el 100% de los casos.

## Assumptions

- "Año" se interpreta como **año calendario** (1 ene – 31 dic). La normativa REPSE se evalúa con bimestres fiscales SAT/IMSS para vencimiento de documentos individuales (spec 001 FR-009), pero el tablero usa año calendario para simplicidad de uso y reportes anuales.
- Los gráficos pueden generarse con cualquier librería de visualización compatible con accesibilidad y branding (decisión técnica para `/speckit-plan`).
- Las etiquetas por proveedor NO forman parte del modelo de datos actual y NO se incluyen como filtro en este spec (confirmado en Clarifications). Si en una fase posterior se introducen, se sumará un filtro adicional sin alterar el resto del tablero.
- El tablero es de **solo lectura**: no edita datos, solo navega. Las acciones de edición se hacen desde el listado/detalle al que el drill-down lleva.
- La zona horaria del tenant se usa de manera consistente; por defecto Ciudad de México.
- La capacidad de exportar el tablero como imagen/PDF queda fuera de alcance de este spec; los reportes formales se generan desde el spec [`004-compliance-reports`](../004-compliance-reports/spec.md).
- Tendencias mes a mes, comparación entre años y dashboards configurables se posponen a una v2 del tablero.
