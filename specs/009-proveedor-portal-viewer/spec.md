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
- ¿Qué se muestra si un documento fue rechazado o invalidado luego de haber sido aceptado?
- ¿Puede un proveedor tener más de una cuenta de usuario asociada a la misma empresa?

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

### Key Entities *(include if feature involves data)*

- **UsuarioProveedor**: Cuenta de usuario del sistema con rol "proveedor", vinculada a exactamente una empresa proveedora. Atributos clave: credenciales de acceso, empresa asociada, estado activo/inactivo.
- **EmpresaProveedora**: Entidad ya existente en el sistema. Representa la empresa cuyos documentos se gestionan.
- **TipoDeDocumento**: Categoría de documentación de cumplimiento requerida (ya existente en el catálogo). Define la periodicidad de vigencia y si es obligatorio.
- **RegistroDeDocumento**: Entrega concreta de un documento para un tipo dado, con fecha de carga, período de vigencia y estado de validación.
- **EstadoDeCumplimiento**: Estado calculado por tipo de documento: vigente, próximo a vencer, vencido o pendiente de entrega.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los administradores pueden crear una cuenta de usuario proveedor y asociarla a su empresa en menos de 2 minutos.
- **SC-002**: El proveedor ve su portal de documentación en menos de 5 segundos desde que inicia sesión.
- **SC-003**: El 100% de los tipos de documento requeridos para la empresa del proveedor son visibles en una sola pantalla sin necesidad de paginación o búsqueda.
- **SC-004**: Los documentos en período de alerta o vencidos se identifican sin leer el texto de estado: mediante color o icono diferenciador.
- **SC-005**: El proveedor puede consultar el historial completo de cualquier tipo de documento en no más de 2 clics desde la pantalla principal del portal.
- **SC-006**: El 95% de los proveedores que interactúan con el portal en pruebas de usabilidad pueden identificar sus documentos en riesgo sin asistencia.

## Assumptions

- Los administradores ya existen en el sistema con capacidad de gestionar el catálogo de empresas y documentos.
- Las empresas proveedoras ya están registradas en el sistema antes de crear la cuenta del usuario proveedor.
- El catálogo de tipos de documento requeridos ya está definido y administrado por los administradores.
- La autenticación de usuarios ya está implementada en el sistema; los proveedores acceden con usuario y contraseña.
- El período de alerta por defecto para documentos "próximos a vencer" es de 30 días antes de la fecha de expiración.
- Un usuario proveedor está vinculado a exactamente una empresa; no se contempla acceso multi-empresa para v1.
- La vista del portal es de solo lectura para el proveedor; no puede cargar ni eliminar documentos desde este portal en v1.
- El diseño responsivo (móvil) es deseable pero secundario respecto a la funcionalidad de escritorio en v1.
- Los roles son mutuamente excluyentes: un usuario no puede ser administrador y proveedor al mismo tiempo.
