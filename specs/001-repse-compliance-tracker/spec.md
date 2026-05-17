# Feature Specification: REPSE Compliance Tracker

**Feature Branch**: `001-repse-compliance-tracker`

**Created**: 2026-05-16

**Status**: Draft

**Input**: User description: "estoy construyendo una aplicacion Saas que gestiona el cumplimiento de los proveedores REPSE bajo la Ley federal del trabajo art 15. El producto gira alrededor del poder gestionar el cumplimiento de las obligaciones del proveedor haciendo una registro de documentacion por cada tipo de archivo de cumplimiento, los cuales pueden tener o no vigencia y varian en mensuales, anuales, bimestrales. El diseño deberia ser moderno minimalista con colores que inspiren confianza y robustez"

## Clarifications

### Session 2026-05-16

- Q: ¿El proveedor REPSE accede al sistema en el MVP para subir su propia documentación, o únicamente el cliente contratante administra y carga documentos por él? → A: Solo el cliente contratante carga; el proveedor NO accede al sistema en v1.
- Q: ¿Cómo se entrega el catálogo de tipos de documento de cumplimiento de fábrica? → A: Catálogo canónico curado por el equipo, precargado para todos los tenants, editable por cada cliente (activar/desactivar/agregar tipos personalizados).
- Q: ¿Cómo se calcula la fecha de vencimiento de un documento con vigencia? → A: Regla por periodicidad anclada al periodo cubierto (mensual = fin del mes siguiente; bimestral = fin del bimestre fiscal SAT/IMSS siguiente; anual = cierre del año fiscal siguiente), con override manual permitido en cada carga.
- Q: ¿Hasta dónde llega el sistema en verificar la autenticidad de los documentos contra SAT/IMSS/INFONAVIT? → A: Sin integraciones a servicios oficiales en v1. Se ofrece (1) OCR best-effort sobre el PDF para prellenar fechas de emisión/vigencia y RFC del proveedor, y (2) verificación manual estructurada: cualquier usuario con permiso puede marcar un documento como "verificado", registrando usuario, fecha y nota opcional. La integración automática con SAT/IMSS/INFONAVIT queda fuera de alcance de v1.
- Q: ¿Cuál es la política de retención de archivos cargados, versiones históricas y bitácora de auditoría? → A: Retención indefinida mientras el tenant esté activo. Al darse de baja la organización, los datos se conservan 90 días en estado de gracia (recuperables por el cliente) y luego se eliminan de forma permanente.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar proveedores y subir su documentación de cumplimiento (Priority: P1)

Un administrador del cliente contratante registra a sus proveedores REPSE en la plataforma, define qué documentos debe entregar cada uno (a partir de un catálogo predefinido) y carga (o permite que el proveedor cargue) los archivos correspondientes. Cada documento queda asociado a un tipo de cumplimiento, a una vigencia (si aplica) y a un periodo (mensual, bimestral o anual).

**Why this priority**: Es el núcleo del producto. Sin la capacidad de registrar proveedores y almacenar sus documentos de cumplimiento, no hay propuesta de valor. Este flujo por sí solo ya constituye un MVP utilizable: una bóveda organizada de documentos REPSE por proveedor.

**Independent Test**: Un usuario crea una cuenta, registra un proveedor, sube un archivo PDF al tipo de documento "Opinión de cumplimiento SAT" y al volver al listado lo ve correctamente clasificado por tipo y con su fecha de carga.

**Acceptance Scenarios**:

1. **Given** un administrador autenticado sin proveedores registrados, **When** registra un nuevo proveedor con razón social y RFC, **Then** el proveedor aparece en el listado del tenant y solo es visible para usuarios de ese tenant.
2. **Given** un proveedor existente, **When** el administrador sube un archivo a un tipo de documento con vigencia mensual indicando el periodo cubierto, **Then** el documento queda registrado con su tipo, periodo, fecha de carga y fecha de vencimiento calculada.
3. **Given** un tipo de documento sin vigencia (p. ej. acta constitutiva), **When** se sube el archivo, **Then** queda registrado como vigente indefinidamente y no genera fechas de expiración.
4. **Given** un archivo cuyo formato o tamaño excede lo permitido, **When** el usuario intenta subirlo, **Then** el sistema rechaza la carga con un mensaje claro y no crea registros parciales.

---

### User Story 2 - Visualizar el estado de cumplimiento por proveedor (Priority: P1)

Cualquier usuario del tenant puede ver, en una sola pantalla por proveedor, el estado de cumplimiento de cada documento requerido: vigente, por vencer, vencido o faltante. Un tablero global muestra el porcentaje de cumplimiento agregado por proveedor y el conteo de documentos en cada estado.

**Why this priority**: La razón por la que un cliente paga por la herramienta es saber "¿quién está al día?" sin abrir 50 archivos. Visualizar el estado es lo que convierte el almacén de archivos en una herramienta de gestión y mitigación de riesgo laboral.

**Independent Test**: Con al menos un proveedor con documentos en distintos estados (vigente, por vencer, vencido, faltante), el usuario abre el detalle del proveedor y observa cada documento etiquetado con su estado correcto, además de un indicador de cumplimiento global del proveedor.

**Acceptance Scenarios**:

1. **Given** un proveedor con todos sus documentos requeridos vigentes, **When** se abre el detalle, **Then** el indicador de cumplimiento muestra 100% y cada documento aparece con estado "Vigente".
2. **Given** un documento con vigencia mensual cargado para el mes anterior, **When** se calcula el estado, **Then** el sistema lo marca como "Vencido" y resalta visualmente la fila.
3. **Given** un documento que vence dentro de los próximos N días configurados (por defecto 15), **When** se calcula el estado, **Then** se muestra como "Por vencer".
4. **Given** un tipo de documento requerido pero sin archivo cargado, **When** se calcula el estado, **Then** aparece como "Faltante" y cuenta en contra del cumplimiento agregado.

---

### User Story 3 - Alertas y recordatorios de vencimiento (Priority: P2)

El sistema notifica proactivamente (por correo y dentro de la aplicación) a los responsables cuando un documento está por vencer o ya venció, y le recuerda al proveedor (si tiene acceso) que debe renovarlo. Las alertas son configurables: días previos al vencimiento y destinatarios.

**Why this priority**: Cierra el ciclo: sin recordatorios automáticos, los usuarios deben revisar manualmente el tablero, y el valor de la herramienta cae. Es importante, pero el producto sigue siendo útil sin él (US1 + US2 ya entregan valor).

**Independent Test**: Configurar un documento con vencimiento dentro de los próximos 7 días y verificar que se envía un correo al responsable definido y que la alerta aparece en el centro de notificaciones del tenant.

**Acceptance Scenarios**:

1. **Given** un documento que vencerá en 15 días y una configuración de alerta a 15 días, **When** corre el proceso diario de evaluación, **Then** se envía exactamente una notificación al/los destinatario(s) configurado(s) ese día.
2. **Given** un documento ya vencido, **When** corre el proceso diario, **Then** se envía un recordatorio diario hasta que el documento sea renovado o el usuario silencie la alerta.
3. **Given** un usuario que renueva el documento dentro del periodo de alerta, **When** sube el archivo nuevo y el sistema lo marca como vigente, **Then** se detienen los recordatorios para ese documento.

---

### User Story 4 - Catálogo configurable de tipos de documento (Priority: P2)

Un administrador del tenant puede revisar el catálogo de tipos de documento de cumplimiento (precargado con los obligatorios bajo LFT Art. 15 y normativa REPSE: opinión SAT, opinión IMSS, opinión INFONAVIT, ICSOE, SISUB, contrato de servicios, etc.), habilitar/deshabilitar los que aplican a su operación y, si lo necesita, agregar tipos personalizados con su propia periodicidad.

**Why this priority**: El catálogo precargado cubre el caso general; personalizarlo es valor incremental para clientes con contratos específicos.

**Independent Test**: Un administrador desactiva un tipo del catálogo y crea uno nuevo "Constancia interna" con periodicidad bimestral; al asignar requisitos a un proveedor, solo aparecen los tipos activos del tenant, incluido el personalizado.

**Acceptance Scenarios**:

1. **Given** un tenant recién creado, **When** el administrador abre el catálogo, **Then** ve los tipos precargados por defecto, cada uno con su periodicidad sugerida (mensual / bimestral / anual / sin vigencia).
2. **Given** un tipo de documento personalizado nuevo, **When** se guarda con nombre, periodicidad y descripción, **Then** queda disponible para asignar a proveedores de ese tenant únicamente.

---

### User Story 5 - Reporte exportable de cumplimiento (Priority: P3)

Un usuario puede exportar a un archivo (CSV o PDF) el reporte de cumplimiento de uno o varios proveedores, con el estado de cada documento, fechas de vigencia y enlaces internos al archivo, para fines de auditoría interna o entrega a un cliente final.

**Why this priority**: Es deseable pero no indispensable para un MVP; los datos ya están en pantalla en US2.

**Independent Test**: Generar el reporte para un proveedor y verificar que el archivo descargado refleja fielmente los estados visibles en pantalla.

**Acceptance Scenarios**:

1. **Given** un proveedor con documentos en varios estados, **When** el usuario solicita la exportación, **Then** recibe un archivo con una fila por documento incluyendo tipo, periodo, estado, fecha de carga y fecha de vencimiento.

---

### Edge Cases

- ¿Qué ocurre si se sube un documento con una fecha de vigencia anterior a la fecha de carga? El sistema lo acepta pero lo marca inmediatamente como "Vencido".
- ¿Qué ocurre si dos archivos son cargados al mismo tipo y periodo para un proveedor? El más reciente se considera vigente; los anteriores quedan archivados como histórico consultable, no se borran.
- ¿Qué pasa si un proveedor es dado de baja teniendo documentos cargados? Se conserva el histórico para auditoría; el proveedor se marca como inactivo y deja de contar en métricas de cumplimiento agregadas.
- ¿Cómo se manejan los documentos sin vigencia cuando cambia el catálogo a "con vigencia"? Los documentos existentes mantienen su estado actual; el cambio solo afecta a cargas posteriores.
- ¿Qué pasa si el correo de notificación no se entrega? El sistema registra el fallo y reintenta hasta un número máximo; la notificación in-app sigue visible.
- ¿Cómo se previene la fuga de información entre tenants? Todas las consultas se filtran por `tenant_id` desde la capa de datos; pruebas automatizadas cubren el caso negativo (tenant A no ve datos de tenant B).
- ¿Qué pasa con un archivo subido por error? Un usuario con permiso puede eliminarlo en una ventana configurable; pasada esa ventana, queda archivado y solo se puede sustituir.

## Requirements *(mandatory)*

### Functional Requirements

**Identidad y multi-tenant**

- **FR-001**: El sistema DEBE permitir registrar una organización (cliente contratante) y crear su primer usuario administrador.
- **FR-002**: El sistema DEBE autenticar a los usuarios mediante correo y contraseña, con contraseñas hasheadas con un algoritmo moderno.
- **FR-003**: El sistema DEBE aislar los datos por organización: ningún usuario debe poder consultar proveedores, documentos ni reportes de otra organización.
- **FR-004**: El sistema DEBE soportar al menos tres roles dentro de la organización: administrador, gestor y consulta (solo lectura).

**Gestión de proveedores**

- **FR-005**: Los usuarios DEBEN poder crear, editar, listar, dar de baja y reactivar proveedores con al menos: razón social, RFC, contacto principal y estado (activo/inactivo).
- **FR-006**: El sistema DEBE validar que el RFC tenga el formato correcto y que sea único dentro de la misma organización.

**Catálogo de tipos de documento**

- **FR-007**: El sistema DEBE incluir un catálogo canónico precargado, único para todos los tenants, mantenido por el equipo del producto, con los tipos de documento obligatorios para cumplir LFT Art. 15 / normativa REPSE (al menos: opinión de cumplimiento SAT, opinión de cumplimiento IMSS, opinión de cumplimiento INFONAVIT, ICSOE, SISUB, contrato de servicios, comprobantes de pago de cuotas obrero-patronales y CFDI de nómina), cada uno con su periodicidad sugerida (mensual, bimestral, anual o sin vigencia).
- **FR-007a**: Cada tipo del catálogo canónico DEBE poder ser activado o desactivado dentro de la organización sin alterar el catálogo base de otros tenants.
- **FR-008**: Un administrador DEBE poder crear tipos personalizados adicionales con nombre, periodicidad y descripción, visibles solo dentro de su organización, sin afectar el catálogo canónico.

**Carga y registro de documentos**

- **FR-009**: Los usuarios del cliente contratante (no el proveedor) DEBEN poder subir archivos (PDF, imágenes y formatos ofimáticos comunes) asociados a un proveedor y a un tipo de documento.
- **FR-009a**: Al cargar un PDF, el sistema DEBE intentar extraer, mediante OCR best-effort, la fecha de emisión, la fecha de vigencia y el RFC del proveedor, y prellenar el formulario de carga con esos valores. El usuario siempre puede corregirlos antes de guardar; los valores finales prevalecen sobre la lectura OCR.
- **FR-009b**: El sistema NO DEBE consultar servicios oficiales (SAT 32-D, IMSS, INFONAVIT) en v1. La verificación automática contra esos servicios queda explícitamente fuera de alcance del MVP. El proveedor no tiene acceso al sistema en v1.
- **FR-010**: Para documentos con vigencia, el sistema DEBE registrar la fecha del periodo cubierto por el documento y calcular la fecha de vencimiento por defecto según la periodicidad del tipo:
  - **Mensual**: vence al final del mes calendario siguiente al periodo cubierto.
  - **Bimestral**: vence al final del bimestre fiscal SAT/IMSS siguiente al periodo cubierto (bimestres oficiales: ene-feb, mar-abr, may-jun, jul-ago, sep-oct, nov-dic).
  - **Anual**: vence al cierre del año fiscal siguiente al periodo cubierto.
  - **Sin vigencia**: no se calcula fecha de vencimiento.
- **FR-010a**: El usuario que carga el documento DEBE poder sobrescribir manualmente la fecha de vencimiento calculada cuando el calendario oficial lo amerite (días inhábiles, prórrogas oficiales, fechas atípicas del proveedor). El override se registra en la bitácora.
- **FR-011**: El sistema DEBE rechazar archivos que excedan el tamaño máximo permitido o cuyo formato no esté en la lista permitida, mostrando un mensaje claro.
- **FR-012**: El sistema DEBE conservar el histórico de versiones por tipo y periodo: una nueva carga no borra la anterior, sino que la archiva.

**Estado de cumplimiento**

- **FR-013**: El sistema DEBE calcular y mostrar el estado de cada documento como uno de: vigente, por vencer, vencido o faltante.
- **FR-013a**: Cada documento cargado DEBE poder ser marcado manualmente como "verificado" por un usuario con permiso, registrando quién verificó, fecha/hora y nota opcional. El estado "verificado" es independiente del estado de vigencia y se muestra como un indicador adicional en el listado y detalle.
- **FR-014**: El umbral "por vencer" DEBE ser configurable por organización (por defecto 15 días).
- **FR-015**: El sistema DEBE mostrar un indicador de cumplimiento agregado por proveedor (porcentaje y conteo por estado) y un tablero general del tenant.

**Notificaciones**

- **FR-016**: El sistema DEBE enviar notificaciones por correo electrónico y dentro de la aplicación cuando un documento esté por vencer o haya vencido, según la configuración del tenant.
- **FR-017**: Los usuarios DEBEN poder definir los destinatarios y la antelación de las alertas por tenant.

**Reportes y auditoría**

- **FR-018**: Los usuarios DEBEN poder exportar el reporte de cumplimiento de uno o varios proveedores a un archivo descargable.
- **FR-019**: El sistema DEBE registrar una bitácora de eventos relevantes (alta/baja/edición de proveedores, carga/eliminación de documentos, cambios de catálogo, overrides manuales de vencimiento, marcas de verificación, accesos administrativos) con marca de tiempo y usuario responsable.
- **FR-019a**: La retención de archivos cargados, versiones históricas y bitácora DEBE ser indefinida mientras la organización (tenant) esté activa. No hay eliminación automática por edad.
- **FR-019b**: Al darse de baja una organización, el sistema DEBE conservar todos sus datos en un estado de gracia recuperable durante 90 días naturales, durante los cuales un administrador puede solicitar reactivación o exportación. Pasados los 90 días, los datos del tenant DEBEN ser eliminados de forma permanente.

**Diseño y experiencia**

- **FR-020**: La interfaz DEBE seguir un estilo visual moderno y minimalista con una paleta que comunique confianza y robustez (tonos azules profundos y neutros, acentos discretos para estados), tipografía sans-serif legible, jerarquía clara y suficiente espacio en blanco.
- **FR-021**: El producto DEBE ser usable en pantallas de escritorio modernas; el soporte para móvil entrega al menos visualización del tablero y detalle de proveedor.

**Seguridad y operación**

- **FR-022**: El sistema DEBE servirse sobre HTTPS en cualquier entorno no local y validar todas las entradas en el servidor.
- **FR-023**: El acceso a los archivos almacenados DEBE requerir autenticación y autorización; no debe ser posible obtener un archivo conociendo solo su URL sin sesión válida.
- **FR-024**: El sistema DEBE limitar la tasa de intentos de autenticación para mitigar abusos.

### Key Entities *(include if feature involves data)*

- **Organización (Tenant)**: Cliente contratante que paga por el servicio. Aísla todos los datos del producto. Atributos: nombre comercial, RFC, contacto, configuración (umbral "por vencer", destinatarios de alertas).
- **Usuario**: Persona con acceso al sistema, pertenece a exactamente una organización (en MVP) y tiene un rol. Atributos: nombre, correo, rol, estado.
- **Proveedor**: Empresa o persona física registrada en el REPSE que presta servicios al tenant. Atributos: razón social, RFC, contacto, estado (activo/inactivo).
- **Tipo de Documento de Cumplimiento**: Categoría obligatoria o personalizada de documento (p. ej. "Opinión SAT", "ICSOE"). Atributos: nombre, descripción, periodicidad (mensual / bimestral / anual / sin vigencia), origen (catálogo / personalizado), activo.
- **Documento Cargado**: Archivo concreto asociado a un proveedor y un tipo, opcionalmente a un periodo. Atributos: tipo, periodo cubierto, fecha de carga, fecha de vencimiento calculada, fecha de vencimiento efectiva (con posible override manual), estado derivado, datos extraídos por OCR (best-effort: fecha emisión, fecha vigencia, RFC), bandera de verificación manual con usuario/fecha/nota, usuario que cargó, referencia al archivo almacenado, versión.
- **Notificación / Alerta**: Evento generado para informar a uno o más destinatarios sobre un documento por vencer o vencido. Atributos: destinatario, canal (correo / in-app), documento referenciado, estado (pendiente / enviada / leída), fecha.
- **Bitácora de Auditoría**: Registro inmutable de acciones relevantes. Atributos: usuario, acción, entidad afectada, fecha/hora, metadatos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede registrar su primer proveedor y cargar su primer documento en menos de 5 minutos desde que entra al sistema por primera vez.
- **SC-002**: El estado de cumplimiento (vigente / por vencer / vencido / faltante) de cualquier proveedor refleja la realidad con cero diferencias respecto a los datos cargados, validado por una auditoría manual sobre 20 proveedores de prueba.
- **SC-003**: El 100% de los documentos con vigencia que se acercan a su fecha de vencimiento genera al menos una notificación dentro de la antelación configurada.
- **SC-004**: El 95% de las acciones principales (abrir tablero, abrir detalle de proveedor, subir un documento) se completan en menos de 2 segundos percibidos por el usuario en condiciones normales de red.
- **SC-005**: Cero incidentes de fuga de datos entre tenants en pruebas automatizadas y manuales: ningún usuario de la organización A puede listar, ver o descargar datos/archivos de la organización B.
- **SC-006**: 80% de los usuarios nuevos completan el flujo "registrar proveedor → cargar primer documento → ver su estado en el tablero" sin asistencia, medido en pruebas de usabilidad con al menos 5 participantes.
- **SC-007**: El reporte exportado coincide al 100% con lo mostrado en pantalla para el mismo conjunto de proveedores y filtros.

## Assumptions

- El producto opera bajo modelo SaaS multi-tenant: cada cliente contratante es un tenant aislado.
- **Confirmado en Clarifications (2026-05-16)**: Los proveedores REPSE no acceden al sistema en el MVP; el cliente contratante carga y administra los documentos en su nombre. Un portal de proveedor con auto-carga queda fuera de alcance para v1 y se considera para una siguiente fase.
- El catálogo precargado se basa en los documentos típicamente exigidos por la Ley Federal del Trabajo Art. 15 y la normativa REPSE vigente (opinión de cumplimiento SAT, opinión IMSS, opinión INFONAVIT, ICSOE, SISUB, contratos de servicios, comprobantes de pago de cuotas obrero-patronales, etc.). El contenido exacto se ajustará con el equipo legal antes del lanzamiento.
- La interfaz se entrega en español de México como único idioma del MVP.
- Las notificaciones del MVP se envían por correo electrónico y se muestran en la aplicación. Otros canales (WhatsApp, SMS) quedan fuera de alcance.
- El almacenamiento de archivos es privado y servido a través de URLs firmadas o equivalentes; nunca expuesto públicamente.
- Periodicidades soportadas en el MVP: mensual, bimestral, anual y "sin vigencia". Otras (trimestral, semestral, etc.) se pueden modelar como tipos personalizados con periodicidad configurable.
- La autenticación inicial es por correo y contraseña; SSO/SAML/OIDC se considera para una fase posterior.
- Los tiempos de respuesta declarados asumen una conexión a internet estable de banda ancha residencial o empresarial estándar.
