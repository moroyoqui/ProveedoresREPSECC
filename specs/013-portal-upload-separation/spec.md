# Feature Specification: Separación de Pantallas de Carga y Consulta en el Portal del Proveedor

**Feature Branch**: `013-portal-upload-separation`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Quiero que los proveedores sean capaces de subir su propia documentación, que pueda definir usuarios con rol de proveedor asociados a un proveedor específico del catálogo con aislamiento total entre proveedores, y que sean totalmente separadas las pantallas que se usan para subir y consultar información, incluyendo los servicios si se considera pertinente."

> **Nota de alcance**: La creación de usuarios con rol proveedor, la asociación a una empresa existente del catálogo, el aislamiento total entre proveedores y la capacidad de carga de documentos ya fueron especificados e implementados en la feature [009-proveedor-portal-viewer](../009-proveedor-portal-viewer/spec.md) (FR-001 a FR-003, US1, US5, US6). Esta feature cubre exclusivamente el delta nuevo: la **separación total de la experiencia del proveedor** — pantallas de consulta y de carga independientes, servicios segregados, y una puerta de entrada (inicio de sesión) y menú propios del portal, sin mezcla con el back-end administrativo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pantallas independientes de consulta y de carga (Priority: P1)

El proveedor, al ingresar al portal, encuentra dos áreas claramente diferenciadas y navegables por separado: una pantalla de **Consulta**, dedicada exclusivamente a visualizar el estado de cumplimiento, vencimientos e historial de su documentación, y una pantalla de **Carga**, dedicada exclusivamente a subir documentos y enviarlos a validación. Ninguna de las dos mezcla funciones de la otra.

**Why this priority**: Es el objetivo central de la feature; sin la separación física de pantallas no existe el resto del comportamiento descrito.

**Independent Test**: Un proveedor autenticado puede navegar a la pantalla de Consulta y verificar que no existe ningún control de carga, y navegar a la pantalla de Carga y verificar que no existe contenido de consulta más allá del mínimo contexto necesario (tipo de documento, período y estado que habilita la carga).

**Acceptance Scenarios**:

1. **Given** un proveedor autenticado en el portal, **When** accede a la pantalla de Consulta, **Then** ve el estado, vencimientos e historial de su documentación sin ningún control para subir archivos ni enviar a validación.
2. **Given** un proveedor autenticado en el portal, **When** accede a la pantalla de Carga, **Then** ve únicamente los tipos de documento y períodos elegibles para carga (estados "Faltante" o "Vencido") con los controles de carga y envío a validación.
3. **Given** el proveedor está en cualquiera de las dos pantallas, **When** observa la navegación del portal, **Then** identifica sin ambigüedad cómo llegar a la otra pantalla en un solo paso.
4. **Given** un usuario intenta acceder a una dirección del portal previa a esta separación (vista combinada), **When** la abre, **Then** el sistema lo lleva a la pantalla de Consulta sin error.

---

### User Story 2 - Navegación con contexto entre consulta y carga (Priority: P2)

Mientras revisa su situación en la pantalla de Consulta, el proveedor detecta un tipo de documento "Faltante" o "Vencido" y puede ir directamente a la pantalla de Carga con ese tipo de documento y período ya preseleccionados, sin volver a buscarlos.

**Why this priority**: La separación de pantallas no debe encarecer el flujo principal del proveedor (detectar un incumplimiento y subsanarlo); el puente con contexto preserva la agilidad que hoy ofrece la vista combinada.

**Independent Test**: Desde un tipo de documento en estado "Faltante" en la pantalla de Consulta, una sola acción lleva al proveedor a la pantalla de Carga con ese tipo y período preseleccionados.

**Acceptance Scenarios**:

1. **Given** la pantalla de Consulta muestra un tipo de documento en estado "Faltante" o "Vencido", **When** el proveedor activa la acción de "ir a cargar" de ese elemento, **Then** llega a la pantalla de Carga con ese tipo de documento y período preseleccionados.
2. **Given** un tipo de documento en estado "Vigente" o "Pendiente de validación" en la pantalla de Consulta, **When** el proveedor lo observa, **Then** no se le ofrece la acción de "ir a cargar" para ese período.
3. **Given** el proveedor completa una carga y un envío a validación en la pantalla de Carga, **When** regresa a la pantalla de Consulta, **Then** el nuevo estado ("Pendiente de validación") es visible sin necesidad de reingresar al portal.

---

### User Story 3 - Segregación de servicios por audiencia (Priority: P3)

Las operaciones que el portal del proveedor utiliza (consultar su documentación, cargar archivos, enviar a validación) están segregadas de las operaciones administrativas, y a su vez las operaciones de consulta del proveedor están segregadas de sus operaciones de carga. Una credencial de proveedor no puede invocar ninguna operación administrativa, y ninguna operación de consulta permite modificar información.

**Why this priority**: Refuerza en la capa de servicios la misma separación visible en pantallas y endurece el aislamiento ya garantizado por la feature 009; es valiosa pero el portal es funcional para el usuario sin que esta segregación sea visible.

**Independent Test**: Con una credencial de proveedor, toda invocación directa a una operación administrativa es rechazada; toda operación clasificada como "consulta" ejecutada por el proveedor no produce ningún cambio en la información almacenada.

**Acceptance Scenarios**:

1. **Given** una credencial válida de usuario proveedor, **When** intenta invocar directamente cualquier operación administrativa (gestión de catálogos, usuarios, documentación de otros proveedores), **Then** la operación es rechazada con una respuesta de acceso denegado.
2. **Given** una credencial válida de usuario administrador, **When** opera sobre sus módulos habituales, **Then** su funcionamiento no se ve afectado por la segregación introducida.
3. **Given** las operaciones de consulta del portal, **When** son invocadas, **Then** ninguna de ellas crea, modifica ni elimina información; las operaciones que modifican información existen únicamente dentro del grupo de operaciones de carga.
4. **Given** una credencial de proveedor de la empresa A, **When** invoca una operación de consulta o de carga indicando recursos de la empresa B, **Then** la operación es rechazada (comportamiento ya garantizado por 009 que esta separación DEBE preservar).

---

### User Story 4 - Acceso y menú independientes para proveedores (Priority: P2)

El proveedor ingresa al sistema por una puerta de entrada propia (página de inicio de sesión dedicada, con dirección e identidad visual distintas a las del acceso administrativo). Tras autenticarse, ve únicamente el menú del portal del proveedor (Consulta y Carga); en ningún momento ve opciones, menús ni pantallas del back-end administrativo, ni los usuarios del back-end ven las del portal.

**Why this priority**: Completa la separación de mundos a nivel de entrada y navegación: evita confusión de los proveedores frente a opciones que no les aplican y reduce la superficie expuesta del back-end hacia usuarios externos.

**Independent Test**: Un proveedor accede por la dirección de entrada del portal, inicia sesión y recorre todo su menú sin encontrar ninguna opción administrativa; un administrador accede por la entrada administrativa y no encuentra las pantallas del portal del proveedor.

**Acceptance Scenarios**:

1. **Given** un usuario proveedor con credenciales activas, **When** ingresa por la página de acceso del portal del proveedor, **Then** se autentica y llega directamente al portal, con un menú que solo contiene las opciones del proveedor (Consulta, Carga y cierre de sesión).
2. **Given** un usuario con rol administrativo, **When** intenta iniciar sesión por la página de acceso del portal del proveedor, **Then** el sistema rechaza el ingreso por esa vía e indica que debe usar el acceso administrativo.
3. **Given** un usuario proveedor, **When** intenta iniciar sesión por la página de acceso administrativa, **Then** el sistema rechaza el ingreso por esa vía e indica que debe usar el acceso del portal del proveedor.
4. **Given** un proveedor autenticado navegando el portal, **When** recorre todas las opciones de su menú, **Then** ninguna opción corresponde a módulos administrativos del back-end.

---

### Edge Cases

- ¿Qué ocurre si el proveedor tiene abierta la pantalla de Carga y, mientras tanto, contabilidad aprueba o rechaza el período que está viendo? La elegibilidad debe revalidarse al confirmar la carga o el envío, no solo al pintar la pantalla.
- ¿Qué pasa con marcadores o accesos directos guardados a la vista combinada anterior? Deben resolver a la pantalla de Consulta, nunca a un error.
- ¿Qué ve el proveedor en la pantalla de Carga cuando no tiene ningún tipo de documento elegible (todo vigente o pendiente de validación)? Debe mostrarse un mensaje positivo de cumplimiento, no una pantalla vacía sin explicación.
- ¿Qué ocurre si un usuario administrador navega a las pantallas del portal del proveedor? El acceso debe negarse o redirigir a su área administrativa, manteniendo la exclusión mutua de roles definida en 009.
- ¿Qué ocurre si un proveedor guarda la dirección del acceso administrativo (o viceversa) e intenta autenticarse ahí? El ingreso por la vía equivocada se rechaza con un mensaje que orienta hacia la puerta correcta, sin revelar si las credenciales eran válidas.
- ¿Qué pasa con las sesiones de proveedor activas iniciadas por el flujo de acceso anterior (login compartido) al momento de liberar esta separación? Deben seguir funcionando o forzar un único reinicio de sesión, nunca quedar en un estado mixto con menú administrativo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El portal del proveedor DEBE ofrecer dos pantallas independientes y navegables por separado: una de **Consulta** (estado de cumplimiento, vencimientos, alertas e historial) y una de **Carga** (subida de archivos y envío a validación).
- **FR-002**: La pantalla de Consulta NO DEBE contener ningún control de carga de archivos ni de envío a validación; es estrictamente de solo lectura.
- **FR-003**: La pantalla de Carga DEBE listar únicamente los tipos de documento y períodos elegibles para carga según las reglas de la feature 009 (estados "Faltante" o "Vencido", sin períodos futuros), junto con el contexto mínimo para identificarlos (tipo, período, estado).
- **FR-004**: Desde un elemento elegible en la pantalla de Consulta, el proveedor DEBE poder llegar a la pantalla de Carga con el tipo de documento y período preseleccionados en una sola acción.
- **FR-005**: La navegación entre ambas pantallas DEBE estar visible de forma permanente dentro del portal y requerir un solo paso en cualquier dirección.
- **FR-006**: Las direcciones de acceso a la vista combinada previa DEBEN resolver a la pantalla de Consulta sin producir errores.
- **FR-007**: Las reglas de negocio de carga y envío a validación definidas en la feature 009 (elegibilidad por estado, bloqueo de períodos futuros, validación de archivos, paquete por tipo+período, transiciones de estado) DEBEN conservarse sin cambios; esta feature solo reorganiza dónde se presentan.
- **FR-008**: Las operaciones disponibles para usuarios proveedor DEBEN estar segregadas de las operaciones administrativas: ninguna credencial de proveedor puede invocar operaciones administrativas, ni siquiera por acceso directo fuera de las pantallas, y viceversa para los módulos exclusivos del proveedor.
- **FR-009**: Dentro de las operaciones del proveedor, las operaciones de consulta DEBEN ser de solo lectura (no crear, modificar ni eliminar información); toda operación que modifica información DEBE pertenecer al grupo de operaciones de carga.
- **FR-010**: La separación de pantallas y servicios NO DEBE debilitar el aislamiento entre proveedores garantizado por 009 (FR-003): toda operación, de consulta o de carga, DEBE seguir validando que los recursos pertenezcan a la empresa del usuario autenticado.
- **FR-011**: Al regresar de la pantalla de Carga a la de Consulta tras una carga o envío exitoso, el estado actualizado DEBE ser visible sin que el proveedor reinicie sesión ni recargue manualmente.
- **FR-012**: El sistema DEBE ofrecer una página de inicio de sesión dedicada para proveedores, con dirección propia e identidad visual diferenciada de la del acceso administrativo del back-end.
- **FR-013**: El acceso de proveedores y el acceso administrativo DEBEN ser mutuamente excluyentes: una credencial con rol proveedor solo puede autenticarse por la entrada del portal, y una credencial administrativa solo por la entrada del back-end. El intento por la vía equivocada DEBE rechazarse con un mensaje que oriente a la puerta correcta, sin revelar la validez de las credenciales.
- **FR-014**: Tras autenticarse, el proveedor DEBE ver un menú de navegación independiente que contenga exclusivamente las opciones del portal (Consulta, Carga, cierre de sesión); ninguna opción, pantalla o menú del back-end administrativo DEBE ser visible ni accesible desde la sesión del proveedor, y viceversa.
- **FR-015**: Las cuentas de usuario proveedor DEBEN seguir creándose y administrándose en el mismo módulo de gestión de usuarios del back-end (definido en 009); el acceso dedicado NO DEBE introducir un registro de cuentas ni un mecanismo de credenciales paralelo.

### Key Entities *(include if feature involves data)*

Esta feature no introduce entidades nuevas; reutiliza las definidas en 009 (UsuarioProveedor, EmpresaProveedora, TipoDeDocumento, RegistroDeDocumento, EstadoDeCumplimiento). El único concepto nuevo es organizativo:

- **Pantalla de Consulta**: agrupación de solo lectura de la información de cumplimiento del proveedor.
- **Pantalla de Carga**: agrupación de las acciones de subida y envío a validación, limitada a elementos elegibles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La pantalla de Consulta contiene cero controles de carga o envío a validación, verificable por inspección en el 100% de sus vistas y estados.
- **SC-002**: Desde la detección de un documento "Faltante" o "Vencido" en la pantalla de Consulta, el proveedor llega a la pantalla de Carga con el contexto preseleccionado en una sola acción (máximo 1 clic adicional respecto al flujo combinado actual).
- **SC-003**: El 100% de los intentos de una credencial de proveedor de invocar operaciones administrativas, y de una credencial administrativa de invocar los módulos exclusivos del proveedor, son rechazados en las pruebas de autorización.
- **SC-004**: El 100% de las operaciones clasificadas como consulta no producen ningún cambio en la información almacenada, verificado por pruebas automatizadas.
- **SC-005**: Todos los flujos del proveedor especificados en 009 (carga, reintento, envío a validación, visualización de rechazo) siguen completándose con éxito tras la separación, sin regresiones en sus criterios de éxito (SC-007 a SC-012 de 009).
- **SC-006**: En pruebas de usabilidad, al menos el 90% de los proveedores identifica sin asistencia cuál pantalla usar para consultar y cuál para cargar.
- **SC-007**: El menú visible en cualquier sesión de proveedor contiene cero opciones administrativas del back-end, verificable por inspección en el 100% de las vistas del portal.
- **SC-008**: Un proveedor que ingresa por su página de acceso llega al portal autenticado en un solo paso de inicio de sesión, sin pasar por ninguna pantalla del back-end.
- **SC-009**: El 100% de los intentos de autenticación por la vía equivocada (proveedor en acceso administrativo o administrador en acceso del portal) son rechazados en las pruebas de autorización.

## Clarifications

### Session 2026-06-11

- Q: ¿Es mejor un login especial para los proveedores, con menú independiente, para que no se mezclen con los usuarios del back-end? → A: Sí — se adopta una página de inicio de sesión dedicada y un menú exclusivo del portal (US4, FR-012 a FR-014). Sin embargo, NO se crea un sistema de cuentas paralelo: las credenciales de proveedor siguen administrándose en el mismo módulo de usuarios del back-end (FR-015); la separación es de puertas de entrada y navegación, no de registro de identidades.

## Assumptions

- La feature 009 está implementada y operativa: usuarios con rol proveedor, asociación a una empresa del catálogo, aislamiento entre proveedores, carga y envío a validación. Esta feature no re-especifica nada de eso.
- **Recomendación adoptada sobre los servicios**: el usuario preguntó si los servicios debían "correr la misma suerte" que las pantallas. Se asume que sí — la segregación de servicios por audiencia (proveedor vs. administrador) y por naturaleza (consulta de solo lectura vs. carga) refuerza la seguridad y simplifica las pruebas de autorización, con costo incremental bajo. Si el usuario prefiere limitar la feature solo a pantallas, los FR-008 y FR-009 pueden recortarse sin afectar al resto.
- La separación es una reorganización de la experiencia y de los servicios existentes; no cambia reglas de negocio, estados ni modelo de datos de 009.
- La exclusión mutua de roles (un usuario no es administrador y proveedor a la vez) se mantiene tal como la define 009.
- El diseño responsivo móvil sigue siendo secundario frente a escritorio, igual que en 009.
- El acceso dedicado de proveedores reutiliza el mecanismo de autenticación existente (mismas credenciales, mismas políticas de contraseña y sesión); solo cambian la puerta de entrada, el destino tras autenticarse y el menú visible.
- La exclusión por vía de acceso (FR-013) se basa en el rol del usuario ya definido en 009; no se introducen roles nuevos.
