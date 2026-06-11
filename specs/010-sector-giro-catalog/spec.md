# Feature Specification: Catálogo de Sectores y Giros para Proveedores

**Feature Branch**: `010-sector-giro-catalog`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "Necesito agregar un catálogo de sectores y un catálogo de giros al catálogo de proveedores para poder identificar clasificaciones adicionales de dichos proveedores. La idea es tener algo así como, por ejemplo, que el sector de un proveedor es construcción, y el giro es plomería, o que el sector es construcción y el giro es obra civil."

## Clarifications

### Session 2026-06-08

- Q: ¿El sistema usa eliminación definitiva (hard delete), desactivación (soft-delete), o ambas para sectores y giros? → A: Solo eliminación definitiva (hard delete). No existe estado activo/inactivo.
- Q: ¿El proveedor puede ver el sector y giro que le fue asignado desde su portal? → A: Sí, en modo solo lectura. El proveedor ve su clasificación pero no puede editarla.
- Q: ¿Quién puede usar el filtro por sector/giro en la lista de proveedores? → A: Todos los roles internos autenticados (no solo administradores); los proveedores (rol `supplier`) quedan excluidos porque no tienen acceso al catálogo general de proveedores.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestionar el catálogo de sectores (Priority: P1)

Un administrador necesita mantener actualizado el catálogo de sectores económicos del sistema. Puede crear nuevos sectores, editar los existentes y eliminarlos cuando ya no sean relevantes y no tengan dependencias.

**Why this priority**: Sin el catálogo de sectores no existe la base para clasificar a los proveedores. Es el requisito fundacional de toda la feature.

**Independent Test**: Se puede probar completamente creando, editando y eliminando sectores desde la interfaz de administración, sin necesidad de tener giros ni proveedores configurados.

**Acceptance Scenarios**:

1. **Given** el administrador está en la sección de catálogos, **When** crea un nuevo sector con nombre único, **Then** el sector aparece disponible en la lista para ser asignado a giros y proveedores.
2. **Given** existe un sector en el catálogo, **When** el administrador edita su nombre, **Then** el cambio se refleja en todos los proveedores que lo tienen asignado.
3. **Given** existe un sector con giros asociados, **When** el administrador intenta eliminarlo, **Then** el sistema impide la eliminación e informa que tiene giros dependientes.
4. **Given** existe un sector sin giros ni proveedores asociados, **When** el administrador lo elimina, **Then** el sector desaparece del catálogo.

---

### User Story 2 - Gestionar el catálogo de giros (Priority: P1)

Un administrador necesita mantener el catálogo de giros empresariales, cada uno vinculado a un sector específico. Puede crear giros dentro de un sector, editarlos y eliminarlos.

**Why this priority**: Los giros son la clasificación más específica del proveedor y dependen de los sectores. Ambos catálogos deben estar disponibles antes de poder clasificar proveedores.

**Independent Test**: Se puede probar creando giros bajo un sector existente y verificando que solo aparecen los giros del sector seleccionado al filtrar por sector.

**Acceptance Scenarios**:

1. **Given** existe el sector "Construcción", **When** el administrador crea el giro "Plomería" bajo ese sector, **Then** "Plomería" queda disponible únicamente dentro del sector "Construcción".
2. **Given** el administrador selecciona un sector en el formulario de giro, **When** guarda el giro, **Then** el giro aparece listado bajo ese sector en el catálogo.
3. **Given** existe un giro asignado a uno o más proveedores, **When** el administrador intenta eliminarlo, **Then** el sistema impide la eliminación e informa cuántos proveedores lo tienen asignado.
4. **Given** existe un giro sin proveedores asignados, **When** el administrador lo elimina, **Then** el giro desaparece del catálogo.

---

### User Story 3 - Asignar sector y giro a un proveedor (Priority: P2)

Al registrar o editar un proveedor, el administrador puede seleccionar el sector económico y el giro específico que lo clasifican. El giro disponible se filtra según el sector elegido.

**Why this priority**: Esta es la operación cotidiana que da valor a los catálogos. Sin ella, los catálogos existen pero no clasifican a nadie.

**Independent Test**: Se puede probar editando un proveedor existente, asignando sector y giro, y verificando que los datos quedan guardados y visibles en el perfil del proveedor.

**Acceptance Scenarios**:

1. **Given** el administrador abre el formulario de un proveedor, **When** selecciona el sector "Construcción", **Then** el selector de giro muestra únicamente los giros pertenecientes a "Construcción".
2. **Given** el administrador selecciona sector y giro de un proveedor, **When** guarda los cambios, **Then** la clasificación queda registrada y visible en el perfil del proveedor.
3. **Given** un proveedor ya tiene sector y giro asignados, **When** el administrador cambia el sector, **Then** el giro se limpia y obliga a seleccionar uno del nuevo sector.
4. **Given** el formulario de proveedor, **When** el administrador deja sector o giro en blanco, **Then** el sistema permite guardar (campos opcionales) pero muestra el proveedor como "sin clasificar".

---

### User Story 4 - Consultar y filtrar proveedores por sector y giro (Priority: P3)

Cualquier usuario interno autenticado con acceso al catálogo de proveedores puede filtrar la lista por sector y/o giro para localizar rápidamente proveedores de una categoría específica. Los proveedores (rol `supplier`) no tienen acceso al catálogo general y por tanto no usan este filtro.

**Why this priority**: Agrega valor analítico a los datos de clasificación. Es deseable pero la feature es funcional sin esta capacidad.

**Independent Test**: Se puede probar con al menos tres proveedores clasificados en diferentes combinaciones de sector/giro, aplicando filtros y verificando que solo aparecen los proveedores correspondientes.

**Acceptance Scenarios**:

1. **Given** la lista de proveedores, **When** el usuario filtra por sector "Construcción", **Then** solo aparecen los proveedores cuyo sector es "Construcción".
2. **Given** el usuario ya filtró por sector, **When** agrega un filtro de giro, **Then** la lista se estrecha a los proveedores con esa combinación sector+giro.
3. **Given** no hay proveedores para la combinación de filtros seleccionada, **When** el usuario aplica el filtro, **Then** la lista muestra un mensaje de "sin resultados" en lugar de aparecer vacía sin explicación.

---

### Edge Cases

- ¿Qué pasa si se intenta crear un sector con el mismo nombre que uno existente? El sistema debe rechazarlo e informar que el nombre ya está en uso.
- ¿Qué pasa si se intenta crear un giro con el mismo nombre dentro del mismo sector? El sistema debe rechazarlo; giros con el mismo nombre en distintos sectores sí están permitidos.
- ¿Qué pasa si el catálogo de sectores está vacío cuando se intenta crear un proveedor? Los campos de sector y giro aparecen deshabilitados con un mensaje que invita a crear sectores primero.
- ¿Qué pasa si un proveedor tiene giro asignado y el giro es movido a otro sector (edición del giro)? El proveedor retiene su clasificación registrada; no se realiza ninguna modificación automática sobre los proveedores afectados.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a usuarios administradores crear, editar y eliminar sectores en un catálogo centralizado.
- **FR-002**: El sistema DEBE garantizar que los nombres de sectores sean únicos en todo el catálogo.
- **FR-003**: El sistema DEBE permitir a usuarios administradores crear, editar y eliminar giros, asociando cada giro a exactamente un sector.
- **FR-004**: El sistema DEBE garantizar que los nombres de giros sean únicos dentro de un mismo sector.
- **FR-005**: El sistema DEBE impedir la eliminación de un sector que tenga giros asociados, mostrando un mensaje explicativo.
- **FR-006**: El sistema DEBE impedir la eliminación de un giro que esté asignado a uno o más proveedores, mostrando cuántos proveedores lo usan.
- **FR-007**: El formulario de proveedor DEBE incluir un selector de sector que liste todos los sectores existentes en el catálogo.
- **FR-008**: El formulario de proveedor DEBE incluir un selector de giro que filtre automáticamente los giros según el sector seleccionado.
- **FR-009**: Al cambiar el sector en el formulario de un proveedor, el sistema DEBE limpiar el giro seleccionado para forzar una nueva elección coherente.
- **FR-010**: Los campos de sector y giro en el proveedor DEBEN ser opcionales; un proveedor puede guardarse sin clasificación.
- **FR-011**: La lista de proveedores DEBE ofrecer filtros por sector y por giro de forma combinable, accesibles para cualquier usuario interno autenticado (no para el rol `supplier`).
- **FR-012**: El perfil del proveedor DEBE mostrar el sector y giro asignados, o indicar "sin clasificar" cuando no estén definidos.
- **FR-013**: El portal del proveedor (acceso con rol `supplier`) DEBE mostrar el sector y giro asignados en modo solo lectura; el proveedor no puede editarlos desde su portal.

### Key Entities

- **Sector**: Clasificación económica de nivel alto (ej. "Construcción", "Manufactura"). Atributos clave: nombre único. No existe estado activo/inactivo; los sectores se eliminan definitivamente cuando no tienen dependencias.
- **Giro**: Especialización dentro de un sector (ej. "Plomería" dentro de "Construcción"). Atributos clave: nombre, sector al que pertenece. El nombre debe ser único dentro de su sector.
- **Proveedor**: Entidad ya existente que recibe dos nuevos atributos de clasificación opcionales: sector asignado y giro asignado. El giro debe pertenecer al sector seleccionado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede crear un sector, agregar giros a él y clasificar un proveedor en menos de 3 minutos en total.
- **SC-002**: El selector de giro en el formulario de proveedor responde al cambio de sector de forma inmediata (sin recarga de página).
- **SC-003**: Al filtrar proveedores por sector y/o giro, los resultados se muestran en menos de 2 segundos para catálogos de hasta 5,000 proveedores.
- **SC-004**: El 100% de los intentos de eliminar un sector o giro con dependencias activas son bloqueados con un mensaje claro al usuario.
- **SC-005**: La clasificación sector/giro de un proveedor es visible en su perfil sin navegación adicional.

## Assumptions

- Los sectores y giros son catálogos globales del sistema, compartidos entre todos los usuarios administradores; no son por cliente o por empresa.
- Un proveedor tiene como máximo un sector y un giro asignado (no clasificaciones múltiples simultáneas).
- Los giros son jerárquicamente dependientes de los sectores: un giro siempre pertenece a exactamente un sector.
- Solo usuarios con rol administrador pueden gestionar los catálogos (crear, editar, eliminar sectores y giros); la asignación a proveedores también es función del administrador. Los proveedores (rol `supplier`) pueden ver su clasificación en modo solo lectura desde su portal, pero no editarla.
- Los campos sector y giro son opcionales en el proveedor para no romper el flujo de registro de proveedores ya existentes que aún no tengan clasificación.
- Los sectores y giros predefinidos (carga inicial) están fuera del alcance de esta feature; el catálogo comienza vacío y se llena desde la interfaz.
- La exportación o reportes por sector/giro están fuera del alcance de esta feature; el filtro en lista es suficiente para v1.
