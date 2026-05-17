# Feature Specification: Bóveda de Cumplimiento REPSE (Core)

**Feature Branch**: `001-repse-compliance-tracker`

**Created**: 2026-05-16

**Status**: Draft

**Input**: User description: "estoy construyendo una aplicacion Saas que gestiona el cumplimiento de los proveedores REPSE bajo la Ley federal del trabajo art 15. El producto gira alrededor del poder gestionar el cumplimiento de las obligaciones del proveedor haciendo una registro de documentacion por cada tipo de archivo de cumplimiento, los cuales pueden tener o no vigencia y varian en mensuales, anuales, bimestrales. El diseño deberia ser moderno minimalista con colores que inspiren confianza y robustez"

## Scope

Este spec cubre el **núcleo** del producto: registro de proveedores, carga de documentos contra un catálogo canónico precargado, y visualización del estado de cumplimiento. Es el spec base del cual dependen las features periféricas. Tres features se segregan en sus propios specs y dependen de éste:

- **Alertas y recordatorios de vencimiento** → [`002-compliance-alerts`](../002-compliance-alerts/spec.md)
- **Administración del catálogo de tipos de documento** → [`003-document-catalog-admin`](../003-document-catalog-admin/spec.md)
- **Reportes exportables de cumplimiento** → [`004-compliance-reports`](../004-compliance-reports/spec.md)

## Clarifications

Las clarificaciones marcadas como **globales** aplican también a los specs 002, 003, 004 y 005. Las marcadas como **locales** aplican solo a este spec.

### Session 2026-05-16

- Q (global): ¿El proveedor REPSE accede al sistema en el MVP para subir su propia documentación, o únicamente el cliente contratante administra y carga documentos por él? → A: Solo el cliente contratante carga; el proveedor NO accede al sistema en v1.
- Q (global): ¿Cómo se entrega el catálogo de tipos de documento de cumplimiento de fábrica? → A: Catálogo canónico curado por el equipo, precargado para todos los tenants, editable por cada cliente (activar/desactivar/agregar tipos personalizados).
- Q (global): ¿Cómo se calcula la fecha de vencimiento de un documento con vigencia? → A: Regla por periodicidad anclada al periodo cubierto (mensual = fin del mes siguiente; bimestral = fin del bimestre fiscal SAT/IMSS siguiente; anual = cierre del año fiscal siguiente), con override manual permitido en cada carga.
- Q (global): ¿Hasta dónde llega el sistema en verificar la autenticidad de los documentos contra SAT/IMSS/INFONAVIT? → A: Sin integraciones a servicios oficiales en v1. Se ofrece (1) OCR best-effort sobre el PDF para prellenar fechas de emisión/vigencia y RFC del proveedor, y (2) verificación manual estructurada: cualquier usuario con permiso puede marcar un documento como "verificado", registrando usuario, fecha y nota opcional. La integración automática con SAT/IMSS/INFONAVIT queda fuera de alcance de v1.
- Q (global): ¿Cuál es la política de retención de archivos cargados, versiones históricas y bitácora de auditoría? → A: Retención indefinida mientras el tenant esté activo. Al darse de baja la organización, los datos se conservan 90 días en estado de gracia (recuperables por el cliente) y luego se eliminan de forma permanente.
- Q (local): ¿Qué acciones cuentan como "actualización" del documento para fines de auditoría visible al usuario? → A: **Cualquier cambio sobre el documento** — sustitución de archivo (nueva versión), override manual de la fecha de vencimiento, marca/anulación de verificación, edición de metadatos. Todas estas acciones actualizan un único par de campos en el documento (`last_updated_by` / `last_updated_at`) que se muestran al usuario; la bitácora completa acción-por-acción sigue viviendo en `audit_log`.
- Q (local): ¿Dónde se muestran las trazas de auditoría visibles del documento (agregado / actualizado / validado) en la UI? → A: (1) En el **detalle del documento** como tres bloques etiquetados con usuario, fecha y hora; (2) en el **listado de documentos del proveedor** como tooltip al pasar sobre la fila o sobre el ícono de estado, mostrando los tres registros resumidos; (3) en un **tab "Historial"** accesible bajo demanda desde el detalle, mostrando la lista cronológica completa de acciones (todas las versiones + todos los cambios) a partir de `audit_log` filtrado por documento.
- Q (local): ¿Las acciones automáticas del sistema (OCR, recálculo de estado, jobs, migraciones) cuentan como "actualización" visible? → A: **No**. Solo las acciones realizadas por un usuario humano modifican los campos visibles `last_updated_by` / `last_updated_at`. Los eventos del sistema se registran en `audit_log` con `actor_user_id = NULL` y aparecen en el tab "Historial" del detalle como entradas etiquetadas "Sistema · <evento>" (p. ej. "Sistema · OCR completado", "Sistema · Estado recalculado") sin alterar los bloques de los tres registros visibles.
- Q (global): ¿Cómo se determinan los documentos requeridos por un proveedor? ¿Todos los del catálogo del tenant o un subconjunto según su industria? → A: Cada proveedor pertenece a un **Tipo de Proveedor** (FK 1:N, NOT NULL). El conjunto de documentos requeridos se deriva del tipo asignado: los `DocumentType` que la asociación `SupplierType ↔ DocumentType` declara para esa industria, con periodicidad heredada del `DocumentType` o sobrescrita por la asociación. Onboarding siembra automáticamente un `SupplierType` "Sin clasificar" con el catálogo canónico completo activo para no bloquear el alta de proveedores. La administración del catálogo de tipos de proveedor y sus requisitos vive en el spec [`003-document-catalog-admin`](../003-document-catalog-admin/spec.md) (extendido a "Administración de Catálogos"). Las plantillas por industria (Construcción, Servicios profesionales, Transporte, Manufactura, Limpieza, Seguridad privada, Outsourcing) se importan bajo demanda desde un wizard.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar proveedores y subir su documentación de cumplimiento (Priority: P1)

Un administrador del cliente contratante registra a sus proveedores REPSE en la plataforma, define qué documentos debe entregar cada uno (a partir del catálogo canónico precargado) y carga los archivos correspondientes. Cada documento queda asociado a un tipo de cumplimiento, a una vigencia (si aplica) y a un periodo (mensual, bimestral, anual o sin vigencia).

**Why this priority**: Es el núcleo del producto. Sin la capacidad de registrar proveedores y almacenar sus documentos de cumplimiento, no hay propuesta de valor. Este flujo por sí solo ya constituye un MVP utilizable: una bóveda organizada de documentos REPSE por proveedor.

**Independent Test**: Un administrador crea una cuenta, registra un proveedor, sube un archivo PDF al tipo de documento "Opinión de cumplimiento SAT" y al volver al listado lo ve correctamente clasificado por tipo y con su fecha de carga.

**Acceptance Scenarios**:

1. **Given** un administrador autenticado sin proveedores registrados, **When** registra un nuevo proveedor con razón social y RFC sin elegir tipo, **Then** el proveedor aparece en el listado del tenant asignado al tipo "Sin clasificar" (que exige el catálogo canónico completo) y solo es visible para usuarios de ese tenant.
1a. **Given** un administrador con catálogo de tipos de proveedor configurado, **When** crea un proveedor y selecciona el tipo "Construcción", **Then** el conjunto de documentos requeridos para ese proveedor proviene de los `DocumentType` asociados a "Construcción", y los demás tipos del catálogo del tenant NO se exigen ni cuentan como "Faltante".
1b. **Given** un proveedor con tipo "Servicios profesionales" (que no exige opinión IMSS) y luego reclasificado a "Construcción" (que sí la exige), **When** el administrador guarda el cambio, **Then** los documentos requeridos se recalculan inmediatamente: la opinión IMSS pasa a ser "Faltante" hasta que se cargue.
2. **Given** un proveedor existente, **When** el administrador sube un archivo a un tipo de documento con vigencia mensual indicando el periodo cubierto, **Then** el documento queda registrado con su tipo, periodo, fecha de carga y fecha de vencimiento calculada conforme a FR-010.
3. **Given** un tipo de documento sin vigencia (p. ej. acta constitutiva), **When** se sube el archivo, **Then** queda registrado como vigente indefinidamente y no genera fechas de expiración.
4. **Given** un archivo cuyo formato o tamaño excede lo permitido, **When** el usuario intenta subirlo, **Then** el sistema rechaza la carga con un mensaje claro y no crea registros parciales.
5. **Given** un PDF cargable, **When** el sistema ejecuta OCR best-effort, **Then** prellena fecha de emisión, fecha de vigencia y RFC del proveedor; el usuario puede corregir esos valores antes de guardar y los valores finales prevalecen.
6. **Given** un documento recién cargado, **When** se abre el detalle, **Then** se muestra el bloque "Agregado por" con el nombre del usuario que lo subió, fecha y hora en la zona horaria del tenant; los bloques "Última actualización" y "Validado" se muestran vacíos / "Sin verificar".
7. **Given** un documento existente, **When** otro usuario sustituye el archivo por una nueva versión, **Then** el bloque "Agregado por" sigue mostrando al usuario original con la fecha de carga original, y el bloque "Última actualización" se actualiza al usuario y momento de la sustitución; el tab "Historial" lista ambas versiones cronológicamente.
8. **Given** un documento ya verificado, **When** se abre el detalle, **Then** el bloque "Validado por" muestra al usuario verificador, la fecha y la nota (si fue capturada).

---

### User Story 2 - Visualizar el estado de cumplimiento por proveedor (Priority: P1)

Cualquier usuario del tenant puede ver, en una sola pantalla por proveedor, el estado de cumplimiento de cada documento requerido: vigente, por vencer, vencido o faltante. Un tablero global muestra el porcentaje de cumplimiento agregado por proveedor y el conteo de documentos en cada estado.

**Why this priority**: La razón por la que un cliente paga por la herramienta es saber "¿quién está al día?" sin abrir 50 archivos. Visualizar el estado convierte el almacén de archivos en una herramienta de gestión y mitigación de riesgo laboral.

**Independent Test**: Con al menos un proveedor con documentos en distintos estados (vigente, por vencer, vencido, faltante), el usuario abre el detalle del proveedor y observa cada documento etiquetado con su estado correcto, además de un indicador de cumplimiento global del proveedor.

**Acceptance Scenarios**:

1. **Given** un proveedor con todos sus documentos requeridos vigentes, **When** se abre el detalle, **Then** el indicador de cumplimiento muestra 100% y cada documento aparece con estado "Vigente".
2. **Given** un documento con vigencia mensual cargado para el mes anterior, **When** se calcula el estado, **Then** el sistema lo marca como "Vencido" y resalta visualmente la fila.
3. **Given** un documento que vence dentro de los próximos N días configurados (por defecto 15), **When** se calcula el estado, **Then** se muestra como "Por vencer".
4. **Given** un tipo de documento requerido **por el tipo del proveedor** pero sin archivo cargado, **When** se calcula el estado, **Then** aparece como "Faltante" y cuenta en contra del cumplimiento agregado. Los tipos de documento que NO requiere su tipo de proveedor no se muestran ni cuentan.
5. **Given** un documento marcado manualmente como "verificado", **When** se abre el detalle, **Then** se muestra un indicador adicional de verificación con usuario y fecha, independiente del estado de vigencia.

---

### Edge Cases

- ¿Qué ocurre si se sube un documento con una fecha de vigencia anterior a la fecha de carga? El sistema lo acepta pero lo marca inmediatamente como "Vencido".
- ¿Qué ocurre si dos archivos son cargados al mismo tipo y periodo para un proveedor? El más reciente se considera vigente; los anteriores quedan archivados como histórico consultable, no se borran.
- ¿Qué pasa si un proveedor es dado de baja teniendo documentos cargados? Se conserva el histórico para auditoría; el proveedor se marca como inactivo y deja de contar en métricas de cumplimiento agregadas.
- ¿Qué pasa con un archivo subido por error? Un usuario con permiso puede eliminarlo en una ventana configurable; pasada esa ventana, queda archivado y solo se puede sustituir.
- ¿Cómo se previene la fuga de información entre tenants? Todas las consultas se filtran por `tenant_id` desde la capa de datos; pruebas automatizadas cubren el caso negativo (tenant A no ve datos de tenant B).
- ¿Qué pasa si el OCR no logra extraer ningún dato del PDF? El formulario se muestra vacío y el usuario captura manualmente; no se bloquea la carga.
- ¿Qué pasa con un documento si el tipo de documento es desactivado en el catálogo del tenant después de haberse cargado? El documento existente permanece en el histórico con su estado actual; deja de aparecer como requisito activo en el indicador agregado.
- ¿Qué pasa si se elimina un tipo de proveedor que tiene proveedores asociados? La eliminación se rechaza; se ofrece "archivar" el tipo. Los proveedores deben reasignarse antes (en bulk o uno a uno). Mientras el tipo esté archivado y haya proveedores asociados, no se permite reasignar otros proveedores a ese tipo.
- ¿Qué pasa si un proveedor está en el tipo "Sin clasificar" y la organización quiere eliminar ese tipo? No se permite eliminar "Sin clasificar" en ningún caso (es de origen `system`); solo se puede vaciar reasignando todos sus proveedores a tipos personalizados.

## Requirements *(mandatory)*

### Functional Requirements

**Identidad y multi-tenant**

- **FR-001**: El sistema DEBE permitir registrar una organización (cliente contratante) y crear su primer usuario administrador.
- **FR-002**: El sistema DEBE autenticar a los usuarios mediante correo y contraseña, con contraseñas hasheadas con un algoritmo moderno.
- **FR-003**: El sistema DEBE aislar los datos por organización: ningún usuario debe poder consultar proveedores, documentos ni reportes de otra organización.
- **FR-004**: El sistema DEBE soportar al menos tres roles dentro de la organización: administrador, gestor y consulta (solo lectura).

**Gestión de proveedores**

- **FR-005**: Los usuarios DEBEN poder crear, editar, listar, dar de baja y reactivar proveedores con al menos: razón social, RFC, contacto principal, estado (activo/inactivo) y **tipo de proveedor** (FK 1:N obligatoria; ver FR-005a).
- **FR-005a**: Cada proveedor DEBE estar asociado a exactamente un **Tipo de Proveedor** del catálogo del tenant. Si el usuario no elige uno al crear, se asigna automáticamente el tipo "Sin clasificar" sembrado por el sistema (que tiene activos todos los tipos canónicos de documento). El usuario puede reasignar el tipo en cualquier momento desde la edición del proveedor; el cambio recalcula los documentos requeridos y el estado de cumplimiento agregado.
- **FR-006**: El sistema DEBE validar que el RFC tenga el formato correcto y que sea único dentro de la misma organización.

**Catálogo canónico (consumo)**

- **FR-007**: El sistema DEBE incluir y exponer un catálogo canónico precargado, único para todos los tenants, mantenido por el equipo del producto, con los tipos de documento obligatorios para cumplir LFT Art. 15 / normativa REPSE (al menos: opinión de cumplimiento SAT, opinión de cumplimiento IMSS, opinión de cumplimiento INFONAVIT, ICSOE, SISUB, contrato de servicios, comprobantes de pago de cuotas obrero-patronales y CFDI de nómina), cada uno con su periodicidad sugerida (mensual, bimestral, anual o sin vigencia). La administración del catálogo (activar/desactivar, agregar tipos personalizados) se especifica en el spec [`003-document-catalog-admin`](../003-document-catalog-admin/spec.md); este spec solo requiere consumir el catálogo en estado precargado.

**Carga y registro de documentos**

- **FR-008**: Los usuarios del cliente contratante (no el proveedor) DEBEN poder subir archivos (PDF, imágenes y formatos ofimáticos comunes) asociados a un proveedor y a un tipo de documento del catálogo.
- **FR-008a**: Al cargar un PDF, el sistema DEBE intentar extraer, mediante OCR best-effort, la fecha de emisión, la fecha de vigencia y el RFC del proveedor, y prellenar el formulario de carga con esos valores. El usuario siempre puede corregirlos antes de guardar; los valores finales prevalecen sobre la lectura OCR.
- **FR-008b**: El sistema NO DEBE consultar servicios oficiales (SAT 32-D, IMSS, INFONAVIT) en v1. La verificación automática contra esos servicios queda explícitamente fuera de alcance del MVP. El proveedor no tiene acceso al sistema en v1.
- **FR-009**: Para documentos con vigencia, el sistema DEBE registrar la fecha del periodo cubierto por el documento y calcular la fecha de vencimiento por defecto según la periodicidad del tipo:
  - **Mensual**: vence al final del mes calendario siguiente al periodo cubierto.
  - **Bimestral**: vence al final del bimestre fiscal SAT/IMSS siguiente al periodo cubierto (bimestres oficiales: ene-feb, mar-abr, may-jun, jul-ago, sep-oct, nov-dic).
  - **Anual**: vence al cierre del año fiscal siguiente al periodo cubierto.
  - **Sin vigencia**: no se calcula fecha de vencimiento.
- **FR-009a**: El usuario que carga el documento DEBE poder sobrescribir manualmente la fecha de vencimiento calculada cuando el calendario oficial lo amerite (días inhábiles, prórrogas oficiales, fechas atípicas del proveedor). El override se registra en la bitácora.
- **FR-010**: El sistema DEBE rechazar archivos que excedan el tamaño máximo permitido o cuyo formato no esté en la lista permitida, mostrando un mensaje claro.
- **FR-011**: El sistema DEBE conservar el histórico de versiones por tipo y periodo: una nueva carga no borra la anterior, sino que la archiva.

**Auditoría visible del documento**

- **FR-011a**: Cada documento DEBE exponer **tres trazas de auditoría visibles para el usuario**, no solo en la bitácora:
  - **Agregado**: usuario que subió el documento (`uploaded_by`) + fecha/hora de carga (`created_at`). Inmutable.
  - **Actualizado**: usuario que realizó el último cambio (`last_updated_by`) + fecha/hora (`last_updated_at`). Se actualiza ante CUALQUIER cambio sobre el documento: sustitución del archivo (nueva versión), override manual de la fecha de vencimiento, marca o anulación de verificación, edición de metadatos. Si no ha habido cambios desde la carga inicial, ambos campos quedan NULL (la UI muestra "—" o se omite).
  - **Validado/Aprobado**: usuario que marcó "verificado" (`verified_by`) + fecha/hora (`verified_at`) + nota opcional (`verified_note`). NULL si nunca se ha verificado.
- **FR-011b**: Cuando un documento es sustituido por una nueva versión, la traza "Agregado" del documento (al considerar el conjunto Proveedor × Tipo × Periodo) DEBE corresponder a la **carga original** (versión 1); la versión nueva queda como "Actualizado". El usuario puede ver el historial de versiones desde el detalle del documento y cada versión conserva su propio `uploaded_by` / `created_at`.
- **FR-011c**: La UI DEBE mostrar las trazas de auditoría visibles de un documento en **tres ubicaciones**:
  - **Detalle del documento**: tres bloques etiquetados ("Agregado por", "Última actualización", "Validado por"), cada uno con nombre del usuario, fecha y hora en la zona horaria del tenant (formato `dd MMM yyyy HH:mm`). Si una traza no aplica todavía (p. ej. nunca verificado), su bloque se muestra como "Sin verificar" sin mostrar usuario/fecha.
  - **Listado de documentos** (en el detalle del proveedor): al pasar el cursor sobre la fila o sobre el ícono de estado, un tooltip muestra los tres registros resumidos en una sola línea por traza.
  - **Tab "Historial"** dentro del detalle del documento: lista cronológica de TODAS las acciones de ese documento (todas las versiones + todos los cambios), construida a partir de `audit_log` filtrado por `entity_type='document'` y `entity_id`. Accesible para todos los roles que tienen visibilidad sobre el documento.
- **FR-011d**: Para el `viewer` (rol de solo consulta), el tab "Historial" DEBE ser visible (consulta), pero los bloques de auditoría del detalle y los tooltips del listado NO DEBEN ocultarse: la trazabilidad de "quién hizo qué" es información operativa básica.
- **FR-011e**: Las **acciones del sistema** (OCR best-effort, recálculo automático de estado, jobs de retención, migraciones de datos, recálculo por cambio de umbral "por vencer") NO DEBEN modificar `last_updated_by` ni `last_updated_at`. Se registran exclusivamente en `audit_log` con `actor_user_id = NULL` y aparecen en el tab "Historial" del documento como entradas etiquetadas "Sistema · <evento>" (p. ej. "Sistema · OCR completado", "Sistema · Estado recalculado a Vencido"). Esto preserva la integridad semántica de los bloques visibles: "Última actualización" siempre apunta a una persona.

**Estado de cumplimiento**

- **FR-012**: El sistema DEBE calcular y mostrar el estado de cada documento como uno de: vigente, por vencer, vencido o faltante.
- **FR-012a**: Cada documento cargado DEBE poder ser marcado manualmente como "verificado" por un usuario con permiso, registrando quién verificó, fecha/hora y nota opcional. El estado "verificado" es independiente del estado de vigencia y se muestra como un indicador adicional en el listado y detalle.
- **FR-012b**: El conjunto de **documentos requeridos** para un proveedor se deriva exclusivamente de su **Tipo de Proveedor**: los `DocumentType` que la asociación `SupplierType ↔ DocumentType` activa para esa industria. Si la asociación define una `periodicity_override`, esa prevalece sobre la periodicidad base del `DocumentType` al calcular la fecha de vencimiento. El estado "Faltante" se evalúa SOLO contra esa lista (no contra todo el catálogo del tenant).
- **FR-013**: El umbral "por vencer" DEBE ser configurable por organización (por defecto 15 días).
- **FR-014**: El sistema DEBE mostrar un indicador de cumplimiento agregado por proveedor (porcentaje y conteo por estado) calculado contra los documentos requeridos por su Tipo de Proveedor (FR-012b), y un tablero general del tenant.

**Auditoría y retención (transversal)**

- **FR-015**: El sistema DEBE registrar una bitácora de eventos relevantes (alta/baja/edición de proveedores, carga/eliminación de documentos, overrides manuales de vencimiento, marcas de verificación, accesos administrativos) con marca de tiempo y usuario responsable.
- **FR-015a**: La retención de archivos cargados, versiones históricas y bitácora DEBE ser indefinida mientras la organización (tenant) esté activa. No hay eliminación automática por edad.
- **FR-015b**: Al darse de baja una organización, el sistema DEBE conservar todos sus datos en un estado de gracia recuperable durante 90 días naturales, durante los cuales un administrador puede solicitar reactivación o exportación. Pasados los 90 días, los datos del tenant DEBEN ser eliminados de forma permanente.

**Diseño y experiencia (transversal)**

- **FR-016**: La interfaz DEBE seguir un estilo visual moderno y minimalista con una paleta que comunique confianza y robustez (tonos azules profundos y neutros, acentos discretos para estados), tipografía sans-serif legible, jerarquía clara y suficiente espacio en blanco. Este lineamiento aplica a todos los specs derivados.
- **FR-017**: El producto DEBE ser usable en pantallas de escritorio modernas; el soporte para móvil entrega al menos visualización del tablero y detalle de proveedor.

**Seguridad y operación (transversal)**

- **FR-018**: El sistema DEBE servirse sobre HTTPS en cualquier entorno no local y validar todas las entradas en el servidor.
- **FR-019**: El acceso a los archivos almacenados DEBE requerir autenticación y autorización; no debe ser posible obtener un archivo conociendo solo su URL sin sesión válida.
- **FR-020**: El sistema DEBE limitar la tasa de intentos de autenticación para mitigar abusos.

### Key Entities *(include if feature involves data)*

- **Organización (Tenant)**: Cliente contratante que paga por el servicio. Aísla todos los datos del producto. Atributos: nombre comercial, RFC, contacto, configuración (umbral "por vencer", destinatarios de alertas), estado (activa / en gracia / eliminada).
- **Usuario**: Persona con acceso al sistema, pertenece a exactamente una organización (en MVP) y tiene un rol. Atributos: nombre, correo, rol, estado.
- **Proveedor**: Empresa o persona física registrada en el REPSE que presta servicios al tenant. Atributos: razón social, RFC, contacto, estado (activo/inactivo).
- **Tipo de Documento de Cumplimiento**: Categoría obligatoria o personalizada de documento (p. ej. "Opinión SAT", "ICSOE"). Atributos: nombre, descripción, periodicidad (mensual / bimestral / anual / sin vigencia), origen (catálogo canónico / personalizado del tenant), activo en el tenant. La administración detallada vive en spec 003.
- **Tipo de Proveedor (SupplierType)**: Industria o categoría operativa del proveedor (p. ej. "Construcción", "Servicios profesionales", "Transporte"). Atributos: nombre, descripción, origen (`system` para "Sin clasificar" auto-sembrado / `custom` para los creados por el tenant), activo. Cada proveedor referencia exactamente uno. Define qué documentos exige y con qué periodicidad. La administración detallada vive en spec 003 (extendido).
- **Requisito por Tipo de Proveedor (SupplierTypeDocumentRequirement)**: Asociación entre un `SupplierType` y un `DocumentType` activo en el tenant. Atributos: tipo de proveedor, tipo de documento, periodicidad efectiva (NULL → hereda del `DocumentType`; valor concreto → override), activa. Sin esta asociación, ese tipo de documento NO se exige a los proveedores de ese tipo.
- **Documento Cargado**: Archivo concreto asociado a un proveedor y un tipo, opcionalmente a un periodo. Atributos: tipo, periodo cubierto, fecha de vencimiento calculada, fecha de vencimiento efectiva (con posible override manual), estado derivado, datos extraídos por OCR (best-effort: fecha emisión, fecha vigencia, RFC), referencia al archivo almacenado, versión, y **tres trazas de auditoría visibles** (FR-011a):
  - **Agregado**: `uploaded_by` (usuario) + `created_at` (fecha/hora). Inmutable.
  - **Actualizado**: `last_updated_by` (usuario, nullable) + `last_updated_at` (fecha/hora, nullable). Cubre cualquier cambio posterior al alta.
  - **Validado**: `verified` (bool) + `verified_by` + `verified_at` + `verified_note`.
- **Bitácora de Auditoría**: Registro inmutable de acciones relevantes. Atributos: usuario, acción, entidad afectada, fecha/hora, metadatos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede registrar su primer proveedor y cargar su primer documento en menos de 5 minutos desde que entra al sistema por primera vez.
- **SC-002**: El estado de cumplimiento (vigente / por vencer / vencido / faltante) de cualquier proveedor refleja la realidad con cero diferencias respecto a los datos cargados, validado por una auditoría manual sobre 20 proveedores de prueba.
- **SC-003**: El 95% de las acciones principales (abrir tablero, abrir detalle de proveedor, subir un documento) se completan en menos de 2 segundos percibidos por el usuario en condiciones normales de red.
- **SC-004**: Cero incidentes de fuga de datos entre tenants en pruebas automatizadas y manuales: ningún usuario de la organización A puede listar, ver o descargar datos/archivos de la organización B.
- **SC-005**: 80% de los usuarios nuevos completan el flujo "registrar proveedor → cargar primer documento → ver su estado en el tablero" sin asistencia, medido en pruebas de usabilidad con al menos 5 participantes.

## Assumptions

- El producto opera bajo modelo SaaS multi-tenant: cada cliente contratante es un tenant aislado.
- **Confirmado en Clarifications (2026-05-16)**: Los proveedores REPSE no acceden al sistema en el MVP; el cliente contratante carga y administra los documentos en su nombre. Un portal de proveedor con auto-carga queda fuera de alcance para v1.
- El catálogo precargado se basa en los documentos típicamente exigidos por la Ley Federal del Trabajo Art. 15 y la normativa REPSE vigente. El contenido exacto se ajustará con el equipo legal antes del lanzamiento.
- La interfaz se entrega en español de México como único idioma del MVP.
- El almacenamiento de archivos es privado y servido a través de URLs firmadas o equivalentes; nunca expuesto públicamente.
- Periodicidades soportadas en el MVP: mensual, bimestral, anual y "sin vigencia". Otras (trimestral, semestral, etc.) se modelan como tipos personalizados con periodicidad configurable (spec 003).
- La autenticación inicial es por correo y contraseña; SSO/SAML/OIDC se considera para una fase posterior.
- Los tiempos de respuesta declarados asumen una conexión a internet estable de banda ancha residencial o empresarial estándar.
- Las features de **alertas** (spec 002), **administración del catálogo** (spec 003) y **reportes exportables** (spec 004) dependen de las entidades y reglas de este spec, pero no son requisito de salida para la primera entrega; cada uno tiene su propio ciclo `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
