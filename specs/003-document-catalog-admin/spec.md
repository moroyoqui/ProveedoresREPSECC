# Feature Specification: Administración del Catálogo de Tipos de Documento

**Feature Branch**: `003-document-catalog-admin`

**Created**: 2026-05-16

**Status**: Draft

**Depends on**: [`001-repse-compliance-tracker`](../001-repse-compliance-tracker/spec.md) (entidad `Tipo de Documento de Cumplimiento`, catálogo canónico precargado en FR-007 del spec 001).

## Scope

Permite a cada organización **personalizar el catálogo** de tipos de documento de cumplimiento sin afectar a otros tenants ni el catálogo canónico. Cubre:

- Activar/desactivar tipos del catálogo canónico dentro del tenant.
- Crear tipos personalizados con nombre, periodicidad y descripción, visibles solo en el tenant.
- Editar y archivar tipos personalizados respetando documentos ya cargados.

Fuera de alcance: gestión del catálogo canónico maestro (eso lo hace el equipo del producto fuera del MVP), versionado complejo de tipos, plantillas por industria.

## Clarifications

Aplica el bloque de **clarificaciones globales** del spec 001 (sesión 2026-05-16), particularmente: el catálogo es canónico curado por el equipo del producto y cada tenant puede activar/desactivar y agregar tipos personalizados.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activar y desactivar tipos del catálogo canónico (Priority: P1)

Un administrador del tenant abre el catálogo, ve la lista canónica precargada y desactiva los tipos que no aplican a su operación. Esos tipos dejan de aparecer al asignar requisitos a proveedores y dejan de contar en el indicador agregado de cumplimiento, pero los documentos previamente cargados sobre ellos se conservan en el histórico.

**Why this priority**: Es el caso 80/20 del feature; sin la capacidad de filtrar, el tablero del cliente se llena de "Faltantes" que en realidad no aplican y el porcentaje de cumplimiento pierde sentido.

**Independent Test**: Desactivar el tipo "ICSOE" en un tenant; al abrir el detalle de un proveedor, ese tipo deja de aparecer como requisito y el indicador agregado se recalcula; otro tenant ve "ICSOE" activo intacto.

**Acceptance Scenarios**:

1. **Given** un tenant recién creado con el catálogo canónico precargado, **When** el administrador desactiva un tipo, **Then** ese tipo deja de aparecer al asignar requisitos a proveedores y deja de contar como "Faltante" en el indicador agregado del tenant.
2. **Given** un tipo desactivado con documentos previamente cargados, **When** se consulta el detalle del proveedor, **Then** los documentos cargados siguen siendo visibles en el histórico marcados como "tipo desactivado", pero no aparecen en la lista de requisitos vigentes.
3. **Given** el tipo "ICSOE" desactivado en el tenant A, **When** se consulta el catálogo en el tenant B, **Then** "ICSOE" sigue activo en B sin alteración.
4. **Given** un tipo desactivado, **When** el administrador lo reactiva, **Then** vuelve a aparecer como requisito en los proveedores y los documentos históricos se reincorporan al cálculo de estado.

---

### User Story 2 - Crear y mantener tipos personalizados del tenant (Priority: P2)

Un administrador agrega un tipo de documento que su operación exige pero no está en el catálogo canónico (p. ej. "Constancia interna de seguridad e higiene") con su periodicidad. El tipo queda disponible para asignar a proveedores **solo dentro de ese tenant**.

**Why this priority**: Cubre los contratos y políticas específicas del cliente; no es indispensable para arrancar (US1 ya entrega la mayor parte del valor con el catálogo canónico), pero es lo que vuelve el producto adaptable.

**Independent Test**: Crear el tipo "Constancia interna" con periodicidad bimestral en el tenant A; al asignar requisitos a un proveedor, el tipo aparece; en el tenant B no aparece.

**Acceptance Scenarios**:

1. **Given** un administrador en la sección de catálogo, **When** crea un tipo personalizado con nombre, periodicidad ("mensual" / "bimestral" / "anual" / "sin vigencia") y descripción, **Then** queda disponible para asignar a proveedores de ese tenant únicamente y aparece marcado como "personalizado".
2. **Given** un tipo personalizado existente, **When** el administrador edita su nombre o descripción, **Then** el cambio se refleja en los requisitos del tenant sin alterar los documentos ya cargados.
3. **Given** un tipo personalizado sin documentos cargados, **When** el administrador lo elimina, **Then** desaparece del catálogo del tenant.
4. **Given** un tipo personalizado con documentos cargados, **When** el administrador intenta eliminarlo, **Then** el sistema impide la eliminación y ofrece "archivar" en su lugar (conserva histórico, deja de pedirse como requisito).

---

### Edge Cases

- ¿Qué pasa si un administrador intenta crear un tipo personalizado con el mismo nombre que un tipo del catálogo canónico? El sistema lo permite si los nombres difieren, pero advierte para evitar duplicados confusos.
- ¿Qué pasa si el nombre del tipo personalizado se repite dentro del mismo tenant? El sistema lo rechaza; el nombre debe ser único por tenant.
- ¿Qué pasa si la periodicidad de un tipo personalizado cambia después de tener documentos cargados? El cambio aplica solo a futuras cargas; los documentos existentes mantienen la periodicidad con la que fueron registrados.
- ¿Qué pasa si se cambia la periodicidad de un tipo del catálogo canónico desde el tenant? No se permite: la periodicidad del catálogo canónico es inmutable por tenant; si el cliente necesita otra periodicidad, debe crear un tipo personalizado.
- ¿Quién puede tocar el catálogo? Solo el rol "administrador" del tenant; los roles "gestor" y "consulta" tienen acceso de solo lectura.
- ¿Qué pasa cuando el equipo del producto agrega un nuevo tipo al catálogo canónico? Aparece automáticamente como activo en todos los tenants nuevos; en tenants existentes aparece como inactivo por defecto, con notificación al administrador, para que decida si lo activa.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE exponer una sección de "Catálogo de tipos de documento" accesible solo a usuarios con rol de administrador del tenant.
- **FR-002**: La sección DEBE mostrar dos vistas: tipos del **catálogo canónico** (origen "producto") y tipos **personalizados** del tenant, diferenciados visualmente.
- **FR-003**: Un administrador DEBE poder activar o desactivar cualquier tipo del catálogo canónico dentro de su tenant. El cambio NO DEBE afectar a otros tenants.
- **FR-004**: Un administrador DEBE poder crear tipos personalizados con: nombre (texto), periodicidad (mensual / bimestral / anual / sin vigencia) y descripción opcional. La periodicidad debe ser una de los valores soportados; no se permite "personalizada".
- **FR-005**: El sistema DEBE garantizar unicidad del nombre de tipo dentro del tenant (canónico + personalizado), rechazando duplicados exactos (insensible a mayúsculas/espacios al inicio o fin).
- **FR-006**: Un administrador DEBE poder editar el nombre y la descripción de un tipo personalizado. La periodicidad puede cambiarse, pero el cambio aplica solo a documentos cargados posteriormente.
- **FR-007**: La periodicidad de los tipos del catálogo canónico NO DEBE ser editable desde el tenant. Si la organización necesita otra periodicidad para un mismo concepto, DEBE crear un tipo personalizado.
- **FR-008**: Un administrador DEBE poder eliminar un tipo personalizado solo si no tiene documentos cargados; en caso contrario, el sistema DEBE ofrecer la opción de "archivar" (deja de pedirse como requisito; conserva el histórico).
- **FR-009**: Al desactivar o archivar un tipo, los documentos previamente cargados a ese tipo DEBEN permanecer visibles en el detalle del proveedor con la etiqueta "tipo inactivo / archivado", y DEBEN dejar de contar como requisitos activos en el indicador de cumplimiento agregado.
- **FR-010**: Al reactivar un tipo previamente desactivado, los documentos cargados existentes DEBEN reincorporarse al cálculo de estado.
- **FR-011**: Todos los cambios al catálogo (activar/desactivar canónico, crear/editar/eliminar/archivar personalizado) DEBEN registrarse en la bitácora con usuario, acción, tipo afectado, fecha/hora y valores anterior/nuevo donde aplique.
- **FR-012**: Cuando el equipo del producto agregue un nuevo tipo al catálogo canónico, el sistema DEBE incorporarlo automáticamente como **inactivo por defecto** en los tenants existentes y notificar al administrador en el centro de notificaciones; en tenants nuevos se entrega activo.

### Key Entities

- **Asociación Tipo-Tenant**: Vincula un tipo del catálogo canónico con una organización y registra si está activo o inactivo en ese tenant. Atributos: tipo canónico, tenant, activo, fecha último cambio, usuario.
- **Tipo Personalizado**: Tipo creado por el tenant. Atributos: nombre, periodicidad, descripción, estado (activo / archivado), tenant propietario, fecha de creación, usuario creador.
- Las entidades `Tipo de Documento de Cumplimiento`, `Documento Cargado` y `Bitácora` están definidas en el spec 001 y son reutilizadas aquí.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede desactivar tipos no aplicables y crear su primer tipo personalizado en menos de 3 minutos desde que abre la sección por primera vez.
- **SC-002**: El catálogo del tenant A puede ser modificado sin que ningún cambio aparezca en el tenant B, validado en pruebas automatizadas multi-tenant.
- **SC-003**: 100% de los documentos cargados antes de desactivar/archivar un tipo siguen siendo recuperables y descargables después del cambio.
- **SC-004**: El indicador de cumplimiento agregado refleja correctamente los cambios de catálogo dentro del mismo día (sin necesidad de procesos manuales adicionales).
- **SC-005**: Cero cambios accidentales al catálogo canónico maestro desde la interfaz del tenant: ninguna acción del cliente puede alterar los valores base que otros tenants observan.

## Assumptions

- Solo el rol "administrador" del tenant puede modificar el catálogo. Roles "gestor" y "consulta" tienen acceso de solo lectura.
- El catálogo canónico maestro lo mantiene el equipo del producto fuera del MVP, mediante migraciones o un panel interno; este spec no cubre esa interfaz interna.
- Las periodicidades disponibles son las fijadas en el spec 001: mensual, bimestral, anual, sin vigencia. Periodicidades adicionales (trimestral, semestral) no se ofrecen en v1.
- Los tipos personalizados existen solo a nivel tenant; no hay compartición entre organizaciones ni "marketplace" de plantillas en v1.
