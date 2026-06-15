# Feature Specification: Asignar Proveedor a Usuario

**Feature Branch**: `014-user-supplier-assign`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Claro, sí es necesario definir el hecho de que dentro de la configuración de usuarios exista un apartado para poderle asignar el proveedor a un determinado usuario."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Asignar proveedor al crear un usuario supplier (Priority: P1)

Un administrador crea un nuevo usuario con rol "proveedor" y, en el mismo formulario de creación, selecciona a cuál empresa proveedora quedará vinculado. Al guardar, ese usuario puede ingresar al portal y ver únicamente la información de su proveedor asignado.

**Why this priority**: Sin esta vinculación, el usuario supplier no puede usar el portal en absoluto — bloquea el flujo completo de carga y consulta de documentos.

**Independent Test**: Crear un usuario supplier con proveedor asignado, iniciar sesión en `/portal/login` y verificar que el portal carga sin error 409.

**Acceptance Scenarios**:

1. **Given** el administrador está en el formulario de creación de usuario y selecciona rol "proveedor", **When** el campo de proveedor se vuelve obligatorio y visible, **Then** el administrador puede buscar y seleccionar un proveedor de la lista activa.
2. **Given** el administrador seleccionó un proveedor y guarda el usuario, **When** el usuario ingresa al portal, **Then** el portal muestra la información del proveedor asignado sin errores.
3. **Given** el administrador selecciona un rol distinto a "proveedor" (admin, manager, viewer), **When** visualiza el formulario, **Then** el campo de proveedor no aparece o está deshabilitado.

---

### User Story 2 — Asignar o cambiar proveedor a un usuario supplier existente (Priority: P2)

Un administrador edita un usuario supplier que no tiene proveedor asignado (o desea reasignarlo a otro proveedor), y desde el panel de edición puede seleccionar o cambiar el proveedor vinculado.

**Why this priority**: Permite corregir usuarios mal configurados y cubrir el caso de reasignación cuando un proveedor cambia de contacto o representante.

**Independent Test**: Tomar un usuario supplier sin `supplier_id`, editar desde el back-office asignando un proveedor, y confirmar que el login al portal ya no produce 409.

**Acceptance Scenarios**:

1. **Given** un usuario supplier existente sin proveedor asignado, **When** el administrador abre su formulario de edición, **Then** el campo de proveedor aparece vacío y editable.
2. **Given** el administrador selecciona un proveedor y guarda, **When** consulta el listado de usuarios, **Then** la fila del usuario muestra el nombre del proveedor asignado.
3. **Given** el administrador desea reasignar el proveedor, **When** cambia la selección y guarda, **Then** el nuevo proveedor queda vinculado y el anterior ya no aparece asociado al usuario.

---

### User Story 3 — Visibilidad del proveedor asignado en el listado de usuarios (Priority: P3)

El administrador puede ver en la tabla de usuarios qué proveedor tiene asignado cada usuario supplier, para auditar la configuración sin tener que abrir cada registro.

**Why this priority**: Mejora la operación diaria del administrador; no bloquea funcionalidad pero reduce fricción al gestionar múltiples usuarios.

**Independent Test**: Con varios usuarios supplier asignados a distintos proveedores, verificar que el listado muestra la columna/campo de proveedor con el nombre correcto.

**Acceptance Scenarios**:

1. **Given** existen usuarios supplier con proveedor asignado, **When** el administrador abre la lista de usuarios, **Then** cada fila muestra el nombre del proveedor vinculado (o "Sin asignar" si no tiene).
2. **Given** un usuario con rol distinto a supplier, **When** aparece en el listado, **Then** la columna de proveedor aparece vacía o no aplica.

---

### Edge Cases

- ¿Qué pasa si el proveedor asignado a un usuario es archivado o desactivado después? El usuario mantiene su vínculo pero el administrador deberá reasignarlo.
- ¿Puede un proveedor tener más de un usuario supplier vinculado? Sí — múltiples contactos del mismo proveedor es un caso válido.
- ¿Puede un usuario supplier quedar sin proveedor asignado? Solo temporalmente; el sistema debe advertir que sin proveedor el usuario no puede usar el portal.
- ¿Qué pasa si se intenta asignar el mismo proveedor a dos usuarios supplier distintos? Debe permitirse (varios contactos por proveedor).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El formulario de creación de usuario DEBE mostrar un campo de selección de proveedor cuando el rol elegido es "proveedor".
- **FR-002**: El campo de proveedor DEBE mostrar únicamente proveedores con estado activo.
- **FR-003**: El campo de proveedor DEBE soportar búsqueda por nombre o RFC del proveedor.
- **FR-004**: El formulario de edición de usuario DEBE permitir asignar o cambiar el proveedor vinculado cuando el usuario tiene rol "proveedor".
- **FR-005**: Al guardar un usuario supplier sin proveedor asignado, el sistema DEBE mostrar una advertencia indicando que el usuario no podrá acceder al portal hasta ser vinculado.
- **FR-006**: El listado de usuarios DEBE incluir el nombre del proveedor asignado para los usuarios con rol "proveedor".
- **FR-007**: Al cambiar el rol de un usuario de "proveedor" a otro rol, el sistema DEBE limpiar el proveedor asignado.
- **FR-008**: La API de creación y edición de usuarios DEBE aceptar el campo `supplier_id` y persistirlo en la base de datos.

### Key Entities

- **Usuario**: Persona con acceso al sistema; tiene un rol (`admin`, `manager`, `viewer`, `supplier`) y opcionalmente un `supplier_id`.
- **Proveedor**: Empresa registrada en el sistema; puede tener cero o más usuarios supplier vinculados.
- **Vínculo usuario-proveedor**: Relación 1-a-N (un proveedor puede tener varios usuarios supplier; cada usuario supplier pertenece a un solo proveedor).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede crear un usuario supplier con proveedor asignado en menos de 2 minutos desde la interfaz de usuarios.
- **SC-002**: Un usuario supplier recién creado con proveedor asignado puede ingresar al portal sin errores en su primer intento.
- **SC-003**: El 100% de los usuarios supplier existentes sin proveedor asignado son identificables visualmente desde el listado de usuarios.
- **SC-004**: La reasignación de proveedor de un usuario existente no requiere más de 3 pasos desde el panel de administración.

## Assumptions

- La columna `supplier_id` en la tabla `users` ya existe en la base de datos — no se requieren migraciones de esquema.
- El campo `supplier_id` ya es aceptado por la API `PATCH /users/{id}` pero la UI no lo expone aún.
- Solo los administradores pueden asignar o cambiar el proveedor vinculado a un usuario.
- Los proveedores disponibles para selección se obtienen del mismo catálogo de proveedores activos ya existente en el sistema.
- El portal del proveedor (spec 013) ya implementa la comprobación de `supplier_id`; esta spec habilita la configuración que lo hace funcionar.
