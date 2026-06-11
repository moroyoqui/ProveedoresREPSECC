# Feature Specification: Nombre de Contacto y Registro REPSE en Proveedor

**Feature Branch**: `011-supplier-contact-repse`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "agregar el dato de nombre de contacto y el dato de registro REPSE al catálogo de proveedores."

## Scope

Este spec cubre la incorporación de dos campos al perfil del proveedor:

1. **Nombre de contacto** — campo textual que identifica a la persona de enlace del proveedor. El campo ya existe en el modelo de datos backend pero no está expuesto en los formularios ni en las vistas del frontend.
2. **Número de folio REPSE** — el número de registro otorgado por la STPS (Secretaría del Trabajo y Previsión Social) cuando el proveedor obtiene su inscripción en el padrón REPSE bajo el Art. 15-A de la LFT. Este campo es nuevo en toda la pila (backend + frontend).

Queda fuera de alcance de este spec: validación automática del folio ante la STPS, alertas de vencimiento del registro REPSE (candidato a futura feature ligada a `002-compliance-alerts`), y control de acceso diferenciado por campo.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Capturar y visualizar nombre de contacto del proveedor (Priority: P1)

El administrador de la organización quiere registrar el nombre de la persona de contacto en cada proveedor, de modo que el equipo sepa a quién dirigirse sin necesidad de consultar sistemas externos.

**Why this priority**: El nombre de contacto ya existe como campo en el backend pero nunca fue expuesto en la interfaz. Es el dato más básico de relación comercial con el proveedor.

**Independent Test**: Abrir el formulario de edición de un proveedor existente, escribir un nombre en "Nombre de contacto", guardar, y verificar que el nombre aparece en la ficha de detalle del proveedor.

**Acceptance Scenarios**:

1. **Given** el formulario de nuevo proveedor está abierto, **When** el usuario escribe un nombre en el campo "Nombre de contacto" y guarda, **Then** el nombre queda guardado y se muestra en la ficha de detalle del proveedor.
2. **Given** un proveedor existente sin nombre de contacto registrado, **When** el administrador abre la edición y completa el campo, **Then** el nombre se actualiza correctamente sin afectar otros datos del proveedor.
3. **Given** un proveedor existente con nombre de contacto, **When** el administrador borra el campo y guarda, **Then** el campo queda en blanco (null) y la ficha refleja "—" o equivalente.
4. **Given** la ficha de detalle de un proveedor, **When** hay nombre de contacto registrado, **Then** se muestra junto a correo y teléfono en la sección de datos de contacto.

---

### User Story 2 — Registrar y visualizar número de folio REPSE del proveedor (Priority: P1)

El administrador necesita registrar el número de folio REPSE de cada proveedor para acreditar que el proveedor está inscrito en el padrón oficial de la STPS y poder exhibirlo ante auditorías o clientes.

**Why this priority**: El folio REPSE es el documento central de toda la gestión de cumplimiento: sin él no hay acreditación posible. Tenerlo asociado directamente al perfil del proveedor evita buscarlo en documentos sueltos.

**Independent Test**: Abrir la edición de un proveedor, ingresar un folio REPSE en el campo correspondiente, guardar, y comprobar que el folio aparece en la ficha de detalle y en el portal del proveedor en modo solo lectura.

**Acceptance Scenarios**:

1. **Given** el formulario de nuevo proveedor, **When** el usuario ingresa un folio REPSE y guarda, **Then** el folio queda almacenado y aparece en la ficha de detalle del proveedor.
2. **Given** un proveedor sin folio REPSE registrado, **When** el administrador lo edita y añade el folio, **Then** el folio se guarda correctamente.
3. **Given** un proveedor con folio REPSE registrado, **When** el proveedor accede a su portal, **Then** el folio es visible en modo solo lectura (sin controles de edición).
4. **Given** el campo de folio REPSE vacío en el formulario, **When** el usuario guarda sin completarlo, **Then** el guardado procede correctamente (el campo es opcional).
5. **Given** un folio REPSE registrado, **When** el administrador lo edita con un nuevo valor, **Then** el registro se actualiza correctamente.

---

### Edge Cases

- ¿Qué pasa si el nombre de contacto excede la longitud máxima? El sistema debe mostrar un error de validación antes de enviar al servidor.
- ¿Qué pasa si el folio REPSE tiene caracteres especiales o formatos variables (guiones, letras, números)? El campo acepta texto libre sin validar el formato exacto, ya que el formato oficial puede variar.
- ¿Qué pasa si un proveedor ya tenía nombre de contacto en BD pero el frontend nunca lo mostraba? Al abrir la edición debe pre-poblar el campo correctamente desde los datos existentes.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar el campo "Nombre de contacto" en el formulario de creación de proveedor (junto a correo y teléfono de contacto).
- **FR-002**: El sistema DEBE mostrar el campo "Nombre de contacto" en el formulario de edición de proveedor, pre-poblado con el valor existente si lo hay.
- **FR-003**: El sistema DEBE mostrar el nombre de contacto en la ficha de detalle del proveedor, agrupado con los demás datos de contacto.
- **FR-004**: El sistema DEBE aceptar el campo "Nombre de contacto" como opcional (puede quedar en blanco).
- **FR-005**: El sistema DEBE agregar el campo "Número de folio REPSE" al perfil del proveedor como campo de texto libre, opcional.
- **FR-006**: El sistema DEBE mostrar el campo "Número de folio REPSE" en los formularios de creación y edición de proveedor.
- **FR-007**: El sistema DEBE mostrar el folio REPSE en la ficha de detalle del proveedor.
- **FR-008**: El sistema DEBE mostrar el folio REPSE en el portal del proveedor en modo solo lectura (sin controles de edición).
- **FR-009**: El sistema DEBE persistir los cambios al nombre de contacto y al folio REPSE al guardar el formulario de edición sin pérdida de los demás datos del proveedor.
- **FR-010**: El nombre de contacto DEBE tener una longitud máxima de 120 caracteres; el folio REPSE DEBE tener una longitud máxima de 60 caracteres. El sistema DEBE rechazar entradas que superen estos límites con un mensaje claro.

### Key Entities

- **Proveedor** (`Supplier`): entidad principal. Se extiende con dos campos opcionales: `contact_name` (string, ya presente en backend, ausente en UI) y `repse_folio` (string, nuevo en toda la pila).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede completar el registro del nombre de contacto y el folio REPSE de un proveedor en menos de 30 segundos desde la pantalla de edición.
- **SC-002**: El folio REPSE y el nombre de contacto aparecen correctamente en la ficha de detalle del proveedor y en el portal del proveedor inmediatamente tras guardar, sin recargar manualmente la página.
- **SC-003**: El 100 % de los proveedores existentes en BD que ya tenían `contact_name` almacenado ven ese dato correctamente pre-poblado al abrir la edición (sin pérdida de datos previos).
- **SC-004**: El campo "Número de folio REPSE" es accesible desde el portal del proveedor en modo de solo lectura, sin requerir permisos de administrador.

---

## Assumptions

- El campo `contact_name` ya existe en el modelo backend y en la tabla de base de datos; no se requiere migración Alembic para él.
- El campo `repse_folio` es completamente nuevo y requiere migración Alembic, extensión del schema Pydantic, y nuevo campo en el formulario.
- El folio REPSE se almacena como texto libre sin validación de formato ante servicios oficiales (fuera de alcance de v1).
- El folio REPSE no tiene fecha de vencimiento gestionada en este spec; si se requiere gestionar su vigencia, se cubrirá en una feature separada vinculada a `002-compliance-alerts`.
- El nombre de contacto y el folio REPSE son campos del administrador; el proveedor los ve en solo lectura desde su portal, sin capacidad de editarlos.
- No se requiere mostrar estos campos en la lista de proveedores (tabla principal); solo en el detalle y en el portal.
