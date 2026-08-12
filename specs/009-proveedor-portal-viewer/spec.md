# Feature Specification: Portal del Proveedor — Visor de Documentación

**Feature Branch**: `009-proveedor-portal-viewer`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Se necesita poder crear usuarios tipo proveedor. a la entrada del sistema tengan acceso a un visor, en donde se les muestre El seguimiento de la documentación histórica y por vencer. Todo esto desglosado por tipo de documento."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Creación de usuario proveedor (Priority: P1)

Un administrador crea una cuenta de usuario con rol "proveedor" y la asocia a una empresa proveedora registrada en el sistema. El nuevo usuario puede iniciar sesión con sus credenciales y accede directamente al portal de documentación de su empresa.

**Why this priority**: Sin este flujo no existe ninguna vía de acceso para los proveedores; es el prerrequisito de todas las demás historias.

**Independent Test**: Un administrador puede crear la cuenta, el proveedor inicia sesión por primera vez y ve su portal sin necesidad de ninguna otra historia implementada.

**Acceptance Scenarios**:

1. **Given** el administrador está en el módulo de gestión de usuarios, **When** crea una cuenta con rol "proveedor" y selecciona la empresa correspondiente, **Then** la cuenta queda activa y asociada a esa empresa.
2. **Given** el usuario proveedor tiene credenciales activas, **When** inicia sesión, **Then** el sistema lo redirige automáticamente al portal de documentación de su empresa.
3. **Given** el usuario proveedor inicia sesión, **When** accede al portal, **Then** únicamente puede ver la documentación de su propia empresa, sin acceso a otras secciones del sistema.

---

### User Story 2 — Vista de estado actual por tipo de documento (Priority: P2)

El proveedor ingresa al portal y ve de un vistazo el estado actual de cada tipo de documento requerido: si está vigente, próximo a vencer o vencido, junto con la fecha de vencimiento correspondiente.

**Why this priority**: Es el núcleo del portal; permite al proveedor saber qué acción necesita tomar sin tener que buscar en historial ni en listas largas.

**Independent Test**: Un proveedor con documentos cargados puede abrir el portal y, sin ninguna acción adicional, identificar qué documentos están al corriente, cuáles vencen pronto y cuáles ya vencieron.

**Acceptance Scenarios**:

1. **Given** el proveedor tiene documentos en varios estados, **When** abre el portal, **Then** ve todos los tipos de documento requeridos agrupados por categoría, cada uno con su estado de cumplimiento.
2. **Given** un tipo de documento tiene fecha de vencimiento dentro del período de alerta, **When** el proveedor ve el portal, **Then** ese tipo de documento aparece visualmente destacado como "próximo a vencer".
3. **Given** un tipo de documento está vencido, **When** el proveedor ve el portal, **Then** aparece claramente marcado como "vencido" con la fecha en que expiró.
4. **Given** un tipo de documento no tiene ningún documento cargado, **When** el proveedor ve el portal, **Then** aparece como "pendiente de entrega".

---

### User Story 3 — Consulta del historial de documentos por tipo (Priority: P3)

El proveedor puede consultar el historial completo de documentos entregados para cada tipo, viendo todas las versiones y períodos anteriores ordenados cronológicamente.

**Why this priority**: Permite al proveedor verificar su trayectoria de cumplimiento y entender qué se entregó en períodos pasados, aunque el portal sea funcional sin esta vista de detalle.

**Independent Test**: Para cualquier tipo de documento, el proveedor puede expandirlo o acceder a su historial y ver todas las entregas previas con fecha de carga y período de vigencia.

**Acceptance Scenarios**:

1. **Given** el proveedor está en el portal, **When** selecciona un tipo de documento, **Then** ve la lista de todos los documentos entregados para ese tipo, ordenados del más reciente al más antiguo.
2. **Given** el historial de un tipo tiene múltiples entradas, **When** el proveedor revisa el historial, **Then** cada entrada muestra: fecha de entrega, período de vigencia (inicio–fin) y estado en ese momento.
3. **Given** un tipo de documento nunca ha tenido entregas, **When** el proveedor consulta su historial, **Then** el sistema muestra un mensaje claro indicando que no hay registros previos.

---

### User Story 5 — Carga de documentos faltantes o vencidos (Priority: P2)

El proveedor puede cargar uno o más documentos directamente desde el portal para cualquier período del mes en curso hacia atrás, siempre que el estado del tipo de documento en ese período sea "Faltante" o "Vencido". No puede cargar documentos para períodos futuros ni para tipos que ya tienen un documento vigente en ese período. El diálogo de carga del portal presenta el mismo aspecto y comportamiento que el diálogo de carga de la interfaz administrativa: lista de archivos con estado individual, validación por archivo y retroalimentación inmediata; el tipo de documento y el período quedan predeterminados por el contexto del portal.

**Why this priority**: Sin esta capacidad, el proveedor solo puede visualizar su situación pero no actuar; la carga es la acción de mayor valor del portal porque reduce la dependencia del administrador para subsanar incumplimientos.

**Independent Test**: Un proveedor con al menos un tipo de documento en estado "Faltante" o "Vencido" puede cargar uno o varios archivos desde el portal sin intervención del administrador, ver el estado individual de cada archivo durante y después de la carga, y el estado del tipo de documento se actualiza en la misma sesión.

**Acceptance Scenarios**:

1. **Given** un tipo de documento tiene estado "Faltante" para el mes en curso, **When** el proveedor selecciona ese tipo y carga uno o más archivos válidos, **Then** el sistema registra cada entrega y actualiza el estado visible en el portal.
2. **Given** un tipo de documento tiene estado "Vencido" para un período pasado, **When** el proveedor accede a ese período e intenta cargar un reemplazo, **Then** el sistema permite la carga y refleja el nuevo estado para ese período.
3. **Given** un tipo de documento tiene estado "Vigente" para el período actual, **When** el proveedor intenta cargar otro documento para ese mismo período, **Then** el sistema bloquea la acción e informa que el período ya está cubierto.
4. **Given** un período futuro (mayor al mes en curso), **When** el proveedor intenta cargar un documento para ese período, **Then** el sistema no ofrece la opción de carga para ese período.
5. **Given** el archivo que el proveedor intenta cargar supera el tamaño máximo permitido o tiene un formato no aceptado, **When** confirma la carga, **Then** el sistema rechaza ese archivo con un mensaje que indica el motivo y los formatos/tamaños aceptados, sin afectar los demás archivos seleccionados.
6. **Given** el proveedor selecciona varios archivos y algunos son inválidos, **When** confirma la carga, **Then** el diálogo muestra el estado individual de cada archivo (éxito, error, pendiente) y permite reintentar solo los que fallaron por causas recuperables.
7. **Given** el proveedor carga el mismo archivo PDF (mismo contenido) que ya fue cargado previamente en otro período o por otro usuario, **When** confirma la carga, **Then** el sistema almacena el archivo sin error de duplicado, dado que el nombre de almacenamiento es siempre único gracias al sufijo UUID.

---

### User Story 6 — Envío a validación por tipo de documento (Priority: P2)

Una vez que el proveedor ha subido todos los archivos necesarios para un tipo de documento en el período correspondiente, el portal muestra un botón de llamada a la acción visualmente prominente ("Enviar a validar") que permite enviar el paquete completo a revisión con un solo clic. Esta acción cambia el estado del tipo de documento a "Pendiente de validación" y queda en cola para ser atendida por el personal de contabilidad. El botón se aplica a nivel de tipo de documento, no de archivo individual, de modo que un solo envío abarca todos los archivos cargados para ese tipo y período.

**Why this priority**: Sin este paso explícito de envío, el personal de contabilidad no tiene señal clara de que el proveedor considera completa su entrega; la distinción entre "subido pero incompleto" y "listo para revisar" es crítica para el flujo de trabajo administrativo.

**Independent Test**: Un proveedor carga uno o más archivos para un tipo de documento en el período actual y, sin ninguna acción adicional del administrador, puede ver y presionar el botón "Enviar a validar". Tras presionarlo, el estado cambia a "Pendiente de validación" y el botón desaparece o queda deshabilitado hasta que contabilidad procese la solicitud.

**Acceptance Scenarios**:

1. **Given** el proveedor ha cargado al menos un archivo para un tipo de documento en un período válido, **When** visualiza ese tipo en el portal, **Then** aparece un botón de llamada a la acción con color destacado (no neutro/gris) etiquetado "Enviar a validar".
2. **Given** el botón "Enviar a validar" está visible, **When** el proveedor lo presiona, **Then** el sistema registra la solicitud de validación, cambia el estado del tipo de documento para ese período a "Pendiente de validación" y el botón deja de estar disponible.
3. **Given** un tipo de documento ya está en estado "Pendiente de validación", **When** el proveedor accede al portal, **Then** el estado es claramente visible y el botón de envío no aparece; el proveedor no puede volver a enviarlo sin que contabilidad procese la solicitud.
4. **Given** el proveedor no ha cargado ningún archivo para un tipo de documento en un período, **When** visualiza ese tipo, **Then** el botón "Enviar a validar" no aparece; primero debe cargar al menos un archivo.
5. **Given** un tipo de documento permite múltiples archivos por período, **When** el proveedor presiona "Enviar a validar", **Then** todos los archivos cargados hasta ese momento para ese tipo y período son enviados juntos en un solo paquete de validación.

---

### User Story 4 — Documentos próximos a vencer con acceso rápido (Priority: P4)

El portal presenta una sección de alertas que agrupa todos los tipos de documento que vencen en el período de alerta, permitiendo al proveedor actuar rápidamente sin recorrer toda la lista.

**Why this priority**: Agiliza la respuesta del proveedor ante vencimientos inminentes; reduce el riesgo de incumplimiento por descuido o falta de visibilidad.

**Independent Test**: Cuando al menos un documento entra en el período de alerta, el proveedor ve esa alerta destacada al ingresar al portal, antes de revisar el detalle por tipo.

**Acceptance Scenarios**:

1. **Given** existen tipos de documento en período de alerta, **When** el proveedor ingresa al portal, **Then** aparece una sección de alerta con esos tipos listados y los días restantes para cada uno.
2. **Given** la sección de alertas está visible, **When** el proveedor hace clic en un ítem de alerta, **Then** es llevado directamente a ese tipo de documento en la vista principal.
3. **Given** ningún documento está en período de alerta ni vencido, **When** el proveedor ingresa al portal, **Then** la sección de alertas no aparece o muestra un mensaje positivo de cumplimiento al día.

---

### Edge Cases

- ¿Qué ocurre si la empresa proveedora asociada al usuario es desactivada por el administrador mientras el proveedor tiene sesión activa?
- ¿Cómo se comporta el portal si el catálogo de tipos de documento requeridos cambia (se agrega o elimina un tipo) mientras el proveedor está activo?
- ¿Qué se muestra si un documento fue rechazado o invalidado luego de haber sido aceptado? ¿Se habilita nuevamente la carga para ese período?
- ¿Puede un proveedor tener más de una cuenta de usuario asociada a la misma empresa?
- ¿Qué sucede si el proveedor inicia una carga y pierde conectividad a mitad de la transferencia?
- ¿Se permite cargar múltiples archivos para un mismo período y tipo de documento, o solo se acepta uno? → **Resuelto**: sí, con máximo configurable por tipo en el catálogo.
- ¿Qué ocurre si el personal de contabilidad rechaza la documentación enviada? ¿El estado regresa al estado previo al envío ("Faltante" o "Vencido") y se habilita nuevamente el botón "Enviar a validar"?
- ¿Puede el proveedor añadir más archivos a un tipo de documento que ya está en estado "Pendiente de validación", o la carga queda bloqueada hasta que contabilidad procese la solicitud? → **Resuelto**: bloqueada; el proveedor debe esperar la resolución de contabilidad.
- ¿Qué año se usa en la ruta de almacenamiento para documentos sin período de cobertura (periodicidad "ninguna")? → Se usa el año calendario del momento de la carga.
- ¿Cómo se construye el sufijo UUID cuando el nombre original no tiene extensión? → Se agrega el sufijo antes de la extensión si existe; si no hay extensión, se agrega al final del nombre.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a los administradores crear cuentas de usuario con rol "proveedor".
- **FR-002**: Al crear una cuenta proveedor, el administrador DEBE poder asociarla a una empresa proveedora registrada en el sistema.
- **FR-003**: Una cuenta proveedor DEBE tener acceso exclusivo a los datos de su empresa; no puede ver información de otros proveedores ni acceder a módulos administrativos.
- **FR-004**: Al iniciar sesión, los usuarios con rol proveedor DEBEN ser redirigidos automáticamente al portal de documentación de su empresa.
- **FR-005**: El portal DEBE mostrar todos los tipos de documento requeridos, organizados por tipo, con el estado de cumplimiento de cada uno.
- **FR-006**: El sistema DEBE calcular y mostrar uno de cuatro estados por tipo de documento: "vigente", "próximo a vencer", "vencido" o "pendiente de entrega".
- **FR-007**: Los tipos de documento con fecha de vencimiento dentro del período de alerta (30 días por defecto) DEBEN aparecer visualmente diferenciados del resto.
- **FR-008**: El portal DEBE incluir una sección de acceso rápido que liste los tipos de documento en período de alerta o vencidos.
- **FR-009**: El proveedor DEBE poder consultar el historial de documentos entregados para cada tipo, con fecha de carga y período de vigencia de cada entrega.
- **FR-010**: El sistema DEBE mostrar las fechas de vencimiento de cada documento activo para que el proveedor pueda planificar sus entregas.
- **FR-011**: El portal DEBE permitir al usuario proveedor cargar un documento para cualquier período desde el mes en curso hacia meses anteriores, sin límite de antigüedad.
- **FR-012**: La opción de carga SOLO DEBE estar disponible cuando el tipo de documento en el período seleccionado se encuentre en estado "Faltante" o "Vencido"; los períodos en estado "Vigente", "Próximo a vencer" o "Pendiente de validación" no permiten nueva carga. El portal DEBE mostrar un mensaje explicativo cuando el proveedor intente cargar en un período bloqueado por estado "Pendiente de validación".
- **FR-013**: El portal NO DEBE ofrecer ni permitir la carga de documentos para períodos futuros (cualquier mes posterior al mes en curso).
- **FR-014**: Tras una carga exitosa, el sistema DEBE recalcular y actualizar el estado del tipo de documento para el período afectado, reflejando el cambio en la vista del portal en la misma sesión.
- **FR-015**: El sistema DEBE validar el archivo antes de aceptarlo: formato (PDF, imagen o los tipos definidos en el catálogo) y tamaño máximo permitido, rechazando la carga con mensaje descriptivo si no cumple los requisitos.
- **FR-016**: Una vez que el proveedor haya cargado al menos un archivo para un tipo de documento en un período válido, el sistema DEBE mostrar un botón de llamada a la acción visualmente prominente, con color distintivo (no neutro ni gris), para enviar el tipo de documento completo a validación.
- **FR-017**: La acción de envío a validación opera al nivel de tipo de documento + período. Un único clic al botón envía todos los archivos cargados para ese tipo y período como un paquete indivisible; no existe envío por archivo individual. El número máximo de archivos permitidos por tipo y período está definido en el catálogo de tipos de documento; el portal DEBE respetar ese límite e informar al proveedor cuando lo alcance.
- **FR-018**: Al presionar el botón de envío, el sistema DEBE cambiar el estado del tipo de documento para ese período a "Pendiente de validación" e inhabilitar o ocultar el botón para ese tipo y período. El proveedor no puede volver a enviarlo hasta que el personal de contabilidad procese la solicitud.
- **FR-020**: Cuando el personal de contabilidad **aprueba** una solicitud en "Pendiente de validación", el sistema DEBE cambiar el estado del tipo de documento para ese período a "Vigente".
- **FR-021**: Cuando el personal de contabilidad **rechaza** una solicitud, el sistema DEBE requerir que ingrese un motivo de rechazo antes de confirmar la acción. El estado del tipo de documento DEBE regresar a su estado previo al envío ("Faltante" o "Vencido") y el motivo de rechazo DEBE ser visible para el proveedor en el portal, habilitando nuevamente la carga y el re-envío.
- **FR-022**: Al presionar "Enviar a validar", el sistema DEBE registrar la fecha y hora exacta del envío asociada al paquete de validación. Este dato DEBE ser accesible para el personal de contabilidad desde su futura interfaz de revisión para permitir priorización por antigüedad.
- **FR-019**: El estado "Pendiente de validación" DEBE ser claramente distinguible de los demás estados en la vista del portal del proveedor. El sistema DEBE persistir los datos del paquete enviado (archivos, fecha de envío, motivo de rechazo si aplica) de modo que el personal de contabilidad pueda acceder a ellos desde la interfaz de revisión que será desarrollada en una feature separada. La interfaz de contabilidad está **fuera del alcance** de esta feature.
- **FR-026**: El sistema DEBE almacenar cada archivo en una ruta que incluya el año del período de cobertura y el identificador del proveedor como segmentos de directorio, siguiendo el patrón `{organización}/{año}/{proveedor}/{documento_id}/v{versión}.{ext}`. Para documentos sin período de cobertura, el año utilizado DEBE ser el año calendario del momento de la carga. Esta estructura garantiza que los archivos de diferentes años y proveedores queden segregados en el sistema de archivos y sean fácilmente localizables para auditoría.
- **FR-027**: Cada archivo almacenado en disco DEBE tener un nombre que combine el nombre original del archivo (sin extensión) con un sufijo UUID v4 único separado por un guión bajo, preservando la extensión original al final (ej. `contrato_enero_a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf`). Este esquema DEBE garantizar que dos cargas del mismo archivo, o de archivos con el mismo nombre pero diferente contenido, nunca colisionen en el sistema de archivos. El nombre original DEBE seguir almacenándose en la base de datos como referencia para el usuario.
- **FR-028**: El diálogo de carga del portal del proveedor DEBE ofrecer las mismas capacidades de selección y retroalimentación que el diálogo de carga de la interfaz administrativa: selección de múltiples archivos en una sola operación, visualización del estado individual de cada archivo (pendiente, subiendo, éxito, error), posibilidad de reintentar archivos fallidos individualmente, y mensajes de error específicos por archivo. A diferencia del diálogo administrativo, el tipo de documento y el período de cobertura DEBEN quedar predeterminados por el contexto del portal y no solicitarse al usuario.

### Key Entities *(include if feature involves data)*

- **UsuarioProveedor**: Cuenta de usuario del sistema con rol "proveedor", vinculada a exactamente una empresa proveedora. Atributos clave: credenciales de acceso, empresa asociada, estado activo/inactivo.
- **EmpresaProveedora**: Entidad ya existente en el sistema. Representa la empresa cuyos documentos se gestionan.
- **TipoDeDocumento**: Categoría de documentación de cumplimiento requerida (ya existente en el catálogo). Define la periodicidad de vigencia y si es obligatorio.
- **RegistroDeDocumento**: Entrega concreta de un documento para un tipo dado. Atributos clave: fecha de carga, período de vigencia, estado de validación, fecha y hora de envío a validación (registrada al presionar "Enviar a validar"), y motivo de rechazo (cuando aplique).
- **EstadoDeCumplimiento**: Estado por tipo de documento y período. Estados posibles y transiciones:
  - "Pendiente de entrega" → (proveedor carga archivo) → "Faltante" con archivo / "Vencido" con archivo → (proveedor presiona "Enviar a validar") → "Pendiente de validación"
  - "Pendiente de validación" → (contabilidad aprueba) → "Vigente"
  - "Pendiente de validación" → (contabilidad rechaza con motivo) → regresa a "Faltante" o "Vencido"; motivo visible al proveedor; re-envío habilitado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los administradores pueden crear una cuenta de usuario proveedor y asociarla a su empresa en menos de 2 minutos.
- **SC-002**: El proveedor ve su portal de documentación en menos de 5 segundos desde que inicia sesión.
- **SC-003**: El 100% de los tipos de documento requeridos para la empresa del proveedor son visibles en una sola pantalla sin necesidad de paginación o búsqueda.
- **SC-004**: Los documentos en período de alerta o vencidos se identifican sin leer el texto de estado: mediante color o icono diferenciador.
- **SC-005**: El proveedor puede consultar el historial completo de cualquier tipo de documento en no más de 2 clics desde la pantalla principal del portal.
- **SC-006**: El 95% de los proveedores que interactúan con el portal en pruebas de usabilidad pueden identificar sus documentos en riesgo sin asistencia.
- **SC-007**: Un proveedor puede completar la carga de un documento faltante o vencido desde que abre el portal en no más de 3 clics y en menos de 2 minutos, asumiendo que el archivo ya está preparado.
- **SC-008**: El estado del tipo de documento cargado se actualiza visualmente en el portal en menos de 3 segundos tras confirmar la carga, sin que el proveedor deba realizar ninguna acción adicional para ver el cambio.
- **SC-009**: El botón "Enviar a validar" es visible sin desplazamiento dentro de la vista del tipo de documento y utiliza un color de acción destacado que lo distingue claramente de botones secundarios o de carga.
- **SC-010**: Tras presionar "Enviar a validar", el estado del tipo de documento cambia a "Pendiente de validación" en menos de 3 segundos y el botón queda inhabilitado, sin que el proveedor deba recargar la página.
- **SC-011**: El sistema nunca rechaza la carga de un archivo válido con un error de "duplicado" cuando el archivo tiene el mismo nombre original que otro ya cargado, independientemente del período, proveedor u organización; la unicidad en disco está garantizada por el sufijo UUID.
- **SC-012**: El proveedor puede cargar varios archivos para el mismo tipo y período en una sola operación desde el portal, con el mismo flujo y retroalimentación que en la interfaz administrativa.

## Clarifications

### Session 2026-05-20

- Q: ¿Cuál es el flujo completo de estados tras el envío a validación? → A: Contabilidad aprueba → "Vigente". Contabilidad rechaza → estado regresa a "Faltante"/"Vencido" con motivo de rechazo obligatorio, visible al proveedor; re-envío habilitado tras corrección.
- Q: ¿Se permiten múltiples archivos por tipo de documento y período? → A: Sí, con un máximo configurable por tipo definido en el catálogo de documentos existente.
- Q: ¿La interfaz para que contabilidad apruebe/rechace solicitudes está en el alcance de esta feature? → A: No. Esta feature solo entrega el cambio de estado a "Pendiente de validación" y los datos del motivo de rechazo. La vista de contabilidad es una feature separada.
- Q: ¿Puede el proveedor cargar archivos adicionales mientras el tipo está en "Pendiente de validación"? → A: No — la carga queda bloqueada hasta que contabilidad apruebe o rechace la solicitud.
- Q: ¿El sistema debe registrar metadatos del envío a validación? → A: Sí — fecha y hora del envío quedan registradas y son accesibles para contabilidad en su futura interfaz; no necesariamente visibles para el proveedor en v1.

## Assumptions

- Los administradores ya existen en el sistema con capacidad de gestionar el catálogo de empresas y documentos.
- Las empresas proveedoras ya están registradas en el sistema antes de crear la cuenta del usuario proveedor.
- El catálogo de tipos de documento requeridos ya está definido y administrado por los administradores.
- La autenticación de usuarios ya está implementada en el sistema; los proveedores acceden con usuario y contraseña.
- El período de alerta por defecto para documentos "próximos a vencer" es de 30 días antes de la fecha de expiración.
- Un usuario proveedor está vinculado a exactamente una empresa; no se contempla acceso multi-empresa para v1.
- El proveedor puede cargar documentos para períodos pasados y el mes en curso, pero solo en estados "Faltante" o "Vencido"; no puede eliminar documentos ya registrados ni cargar para períodos futuros.
- El tamaño máximo de archivo y los formatos permitidos los define el catálogo de tipos de documento ya existente en el sistema; el portal usa esas reglas directamente.
- El diseño responsivo (móvil) es deseable pero secundario respecto a la funcionalidad de escritorio en v1.
- Los roles son mutuamente excluyentes: un usuario no puede ser administrador y proveedor al mismo tiempo.
- La interfaz para que el personal de contabilidad apruebe o rechace solicitudes en "Pendiente de validación" está **fuera del alcance** de esta feature; será desarrollada en una feature independiente. Esta feature solo entrega el modelo de datos y el cambio de estado necesario para soportar esa futura interfaz.
- El nombre original del archivo se conserva en la base de datos para mostrarse al usuario; la ruta física en disco incorpora un sufijo UUID para garantizar unicidad sin depender del contenido (SHA256) como único mecanismo de deduplicación.
- La estructura de directorios por año se basa en el año del período de cobertura del documento; si el documento no tiene período (periodicidad "ninguna"), se usa el año de carga.
