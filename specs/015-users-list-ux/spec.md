# Feature Specification: Mejoras UX a la tabla de usuarios

**Feature Branch**: `015-users-list-ux`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Quiero que el greet se muestre toda la información pertinente y que sea responsivo. Quiero que quites la el dato del último acceso. Quiero que además agregues una consulta, una forma de consulta de todos los datos del del del usuario. Cuando le hagas clic al nombre, entonces el nombre en el greet debe de quedar clic y hable con un link ahí, Los botones de contraseña, deshabilitar y asignar proveedor, si quieres mejor, déjalos en puro ícono, y cuando hagas hover que despliegue el tooltip de la acción."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Nombre clickeable abre panel de detalle (Priority: P1)

Un administrador ve la lista de usuarios y hace clic en el nombre de un usuario para ver toda su información: correo, rol, proveedor asociado, estado de cuenta y fecha de creación.

**Why this priority**: Es el flujo principal de consulta. Permite inspeccionar cualquier usuario sin salir de la pantalla de listado.

**Independent Test**: Basta con tener al menos un usuario en la tabla; hacer clic en su nombre debe mostrar el panel/modal con sus datos completos.

**Acceptance Scenarios**:

1. **Given** la tabla de usuarios está cargada, **When** el administrador hace clic en el nombre de un usuario, **Then** se abre un panel o modal que muestra: nombre, correo, rol, estado, proveedor asignado (si aplica) y fecha de creación.
2. **Given** el panel de detalle está abierto, **When** el administrador hace clic en "Cerrar" o fuera del panel, **Then** el panel se cierra sin modificar datos.
3. **Given** el usuario tiene rol distinto a "Proveedor", **When** se abre su panel de detalle, **Then** el campo "Proveedor" muestra "—" o está oculto.

---

### User Story 2 — Acciones representadas solo con íconos y tooltip (Priority: P2)

El administrador ve los botones de acción (Contraseña, Deshabilitar/Habilitar, Asignar proveedor) como íconos compactos. Al hacer hover sobre cada ícono aparece un tooltip con el nombre de la acción.

**Why this priority**: Reduce el espacio horizontal que consumen las acciones, permitiendo que todas sean visibles sin truncarse.

**Independent Test**: Con la tabla cargada, pasar el cursor sobre cada ícono de acción debe mostrar el tooltip correspondiente; hacer clic debe ejecutar la acción correcta.

**Acceptance Scenarios**:

1. **Given** la tabla está cargada, **When** el administrador pasa el cursor sobre el ícono de contraseña, **Then** se muestra el tooltip "Cambiar contraseña".
2. **Given** el usuario está activo, **When** el administrador pasa el cursor sobre el ícono de deshabilitar, **Then** se muestra el tooltip "Deshabilitar".
3. **Given** el usuario está deshabilitado, **When** el administrador pasa el cursor sobre el ícono de habilitar, **Then** se muestra el tooltip "Habilitar".
4. **Given** el usuario tiene rol "Proveedor", **When** el administrador pasa el cursor sobre el ícono de asignar proveedor, **Then** se muestra el tooltip "Asignar proveedor".
5. **Given** el administrador hace clic en cualquier ícono de acción, **Then** se ejecuta la misma acción que antes ejecutaban los botones con texto.

---

### User Story 3 — Tabla responsiva sin columna de último acceso (Priority: P3)

La tabla se adapta a diferentes anchos de pantalla y no muestra la columna "Último acceso". En pantallas angostas, las columnas menos críticas se ocultan o la tabla hace scroll horizontal.

**Why this priority**: Mejora la usabilidad en pantallas medianas y consolida la información relevante.

**Independent Test**: Eliminar la columna "Último acceso" y verificar que la tabla sigue siendo funcional y que en viewport estrecho (< 768 px) las acciones siguen accesibles.

**Acceptance Scenarios**:

1. **Given** la tabla de usuarios está cargada, **Then** no existe ninguna columna titulada "Último acceso".
2. **Given** un viewport de 768 px o más, **Then** todas las columnas principales (Nombre, Correo, Rol, Proveedor, Estado, Acciones) son visibles sin scroll horizontal.
3. **Given** un viewport inferior a 768 px, **Then** la tabla permite scroll horizontal o colapsa columnas secundarias para que las acciones sigan alcanzables.

---

### Edge Cases

- ¿Qué ocurre si un usuario con rol "Proveedor" no tiene proveedor asignado? → el campo debe mostrar "Sin asignar".
- ¿Qué pasa si el panel de detalle se abre para el propio usuario administrador? → se muestra igual, pero las acciones destructivas (Deshabilitar) permanecen deshabilitadas como ya lo están.
- ¿Qué sucede si la lista de usuarios está vacía? → el estado vacío existente se mantiene sin cambios.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El campo "Último acceso" DEBE ser eliminado de la tabla de usuarios.
- **FR-002**: El nombre de cada usuario en la tabla DEBE ser un elemento clicable (enlace o botón con apariencia de enlace).
- **FR-003**: Al hacer clic en el nombre, el sistema DEBE mostrar un panel o modal con los datos completos del usuario: nombre, correo, rol, estado, proveedor asignado y fecha de creación.
- **FR-004**: Los botones de acción (Contraseña, Deshabilitar/Habilitar, Asignar proveedor) DEBEN reemplazarse por íconos sin texto visible.
- **FR-005**: Cada ícono de acción DEBE mostrar un tooltip descriptivo al hacer hover que indique la acción que ejecuta.
- **FR-006**: La tabla DEBE ser responsiva: en viewports anchos (≥ 768 px) todas las columnas son visibles; en viewports estrechos (< 768 px) la tabla permite scroll horizontal o aplica colapso de columnas secundarias.
- **FR-007**: Las restricciones de seguridad actuales DEBEN preservarse: el administrador no puede deshabilitar su propia cuenta; los íconos de acción aplican las mismas reglas de habilitación/deshabilitación que los botones anteriores.

### Key Entities

- **Usuario**: nombre, correo, rol (admin/manager/viewer/supplier), estado (activo/deshabilitado), proveedor asignado (opcional, solo para rol supplier), fecha de creación.
- **Proveedor**: nombre legal y RFC; referenciado desde el detalle del usuario cuando el rol es "supplier".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El administrador puede consultar todos los datos de un usuario con un solo clic, sin navegar a otra página.
- **SC-002**: La columna "Último acceso" no aparece en ningún estado de la tabla (cargando, vacío, con datos).
- **SC-003**: Todas las acciones (contraseña, deshabilitar/habilitar, asignar proveedor) se ejecutan correctamente desde los íconos; ninguna acción se pierde respecto a la versión anterior.
- **SC-004**: En un viewport de 1280 px, los íconos de acción son visibles completos para todos los usuarios de la tabla sin truncarse ni hacer scroll horizontal.
- **SC-005**: El tooltip de cada ícono de acción es legible y se muestra en menos de 300 ms tras el hover.

## Assumptions

- El panel de detalle es de solo lectura; las ediciones se siguen haciendo mediante los íconos de acción (diálogos existentes).
- El campo "fecha de creación" ya está disponible en la respuesta de la API de usuarios; si no lo está, se omite del panel de detalle sin bloquear la feature.
- No se requiere paginación del panel de detalle ni historial de cambios.
- La accesibilidad básica (aria-label en íconos) es suficiente para esta iteración; WCAG AA completo queda fuera de alcance.
- El colapso de columnas en móvil se resuelve con scroll horizontal en la tabla, no con un diseño de tarjetas alternativo.
