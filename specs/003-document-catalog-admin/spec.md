# Feature Specification: Administración de Catálogos (Documentos + Proveedores)

**Feature Branch**: `003-document-catalog-admin`

**Created**: 2026-05-16

**Updated**: 2026-05-16 — alcance ampliado a tipos de proveedor + asociación de requisitos + plantillas por industria.

**Status**: Draft

**Depends on**: [`001-repse-compliance-tracker`](../001-repse-compliance-tracker/spec.md) (entidades `DocumentType`, `SupplierType`, `SupplierTypeDocumentRequirement` y FR-005a, FR-007, FR-012b del spec 001).

## Scope

Permite a cada organización **administrar tres catálogos** que rigen el cumplimiento de sus proveedores, sin afectar a otros tenants ni al catálogo canónico maestro:

1. **Catálogo de Tipos de Documento**: activar/desactivar tipos canónicos, crear tipos personalizados.
2. **Catálogo de Tipos de Proveedor**: crear, editar y archivar tipos de proveedor (industrias) propios del tenant.
3. **Asociación Tipo de Proveedor ↔ Tipos de Documento**: definir qué documentos exige cada tipo de proveedor y con qué periodicidad (heredada del DocumentType o sobreescrita por la asociación).

Además, ofrece un **wizard "Importar plantilla por industria"** que precarga tipos de proveedor canónicos (Construcción, Servicios profesionales, Transporte, Manufactura, Limpieza, Seguridad privada, Outsourcing/Staffing) con sus requisitos típicos, editables tras importar.

Fuera de alcance: gestión del catálogo canónico maestro (lo hace el equipo de producto fuera del MVP), versionado complejo de tipos, periodicidades distintas a {mensual, bimestral, anual, sin vigencia}, compartición de catálogos entre tenants ("marketplace").

## Clarifications

Aplica el bloque de **clarificaciones globales** del spec 001 (sesión 2026-05-16), en particular:

- Periodicidades soportadas: mensual / bimestral / anual / sin vigencia.
- Multi-tenant: ningún cambio en el catálogo de un tenant afecta a otros.
- Cada proveedor pertenece a exactamente un `SupplierType` (1:N obligatoria). Onboarding siembra "Sin clasificar" automáticamente.
- Las asociaciones `SupplierType ↔ DocumentType` pueden tener `periodicity_override`; si NULL, hereda del `DocumentType`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activar y desactivar tipos del catálogo canónico de DOCUMENTOS (Priority: P1)

Un administrador del tenant abre el catálogo de tipos de documento, ve la lista canónica precargada y desactiva los tipos que no aplican a su operación. Esos tipos dejan de poderse asignar como requisitos a tipos de proveedor y dejan de contar en cualquier indicador agregado, pero los documentos previamente cargados sobre ellos se conservan en el histórico.

**Why this priority**: Es el caso 80/20 del feature original (anterior a la ampliación); sin desactivar lo que no aplica, el catálogo se vuelve ruido.

**Independent Test**: Desactivar el tipo "ICSOE" en un tenant; al editar un tipo de proveedor "Servicios profesionales", "ICSOE" deja de ofrecerse como requisito asignable; otro tenant ve "ICSOE" activo intacto.

**Acceptance Scenarios**:

1. **Given** un tenant recién creado con el catálogo canónico precargado, **When** el administrador desactiva un tipo, **Then** ese tipo deja de ofrecerse al asignar requisitos a tipos de proveedor y deja de contar como "Faltante" en el indicador agregado del tenant.
2. **Given** un tipo desactivado con documentos previamente cargados, **When** se consulta el detalle del proveedor, **Then** los documentos cargados siguen siendo visibles en el histórico marcados como "tipo desactivado", pero no aparecen en la lista de requisitos vigentes.
3. **Given** el tipo "ICSOE" desactivado en el tenant A, **When** se consulta el catálogo en el tenant B, **Then** "ICSOE" sigue activo en B sin alteración.
4. **Given** un tipo desactivado, **When** el administrador lo reactiva, **Then** vuelve a ofrecerse como requisito asignable y los documentos históricos se reincorporan al cálculo de estado de los proveedores cuyos tipos lo exigen.

---

### User Story 2 - Crear y mantener tipos personalizados de DOCUMENTO (Priority: P2)

Un administrador agrega un tipo de documento que su operación exige pero no está en el catálogo canónico (p. ej. "Constancia interna de seguridad e higiene") con su periodicidad. El tipo queda disponible para asignar como requisito a tipos de proveedor **solo dentro de ese tenant**.

**Why this priority**: Cubre los contratos y políticas específicas del cliente; no es indispensable para arrancar pero vuelve el producto adaptable.

**Independent Test**: Crear el tipo "Constancia interna" con periodicidad bimestral en el tenant A; al editar un tipo de proveedor del tenant, el tipo aparece como opción; en el tenant B no aparece.

**Acceptance Scenarios**:

1. **Given** un administrador en la sección de catálogo, **When** crea un tipo personalizado con nombre, periodicidad y descripción, **Then** queda disponible para asociar a tipos de proveedor de ese tenant únicamente y aparece marcado como "personalizado".
2. **Given** un tipo personalizado existente, **When** el administrador edita su nombre o descripción, **Then** el cambio se refleja en los requisitos del tenant sin alterar los documentos ya cargados.
3. **Given** un tipo personalizado sin documentos cargados y sin asociaciones a tipos de proveedor, **When** el administrador lo elimina, **Then** desaparece del catálogo del tenant.
4. **Given** un tipo personalizado con documentos cargados o asociado a uno o más tipos de proveedor, **When** el administrador intenta eliminarlo, **Then** el sistema impide la eliminación y ofrece "archivar" en su lugar.

---

### User Story 3 - Administrar el catálogo de TIPOS DE PROVEEDOR (Priority: P1)

Un administrador del tenant abre la sección "Tipos de proveedor", ve la lista actual (al menos el tipo "Sin clasificar" sembrado por el sistema) y puede crear nuevos tipos personalizados como "Construcción", "Servicios profesionales", etc. Cada tipo tiene nombre, descripción opcional y estado (activo/archivado).

**Why this priority**: Sin tipos de proveedor con requisitos diferenciados, el indicador de cumplimiento sigue siendo impreciso (la queja que motivó esta extensión). Es P1 porque desbloquea US4 y todos los specs derivados (alertas, dashboard, reportes) que ahora derivan documentos requeridos del tipo de proveedor.

**Independent Test**: Crear el tipo "Construcción" en el tenant A; verificar que aparece en el selector al crear/editar un proveedor en el tenant A y NO aparece en el tenant B.

**Acceptance Scenarios**:

1. **Given** un tenant recién creado, **When** un administrador abre la sección "Tipos de proveedor", **Then** ve al menos el tipo "Sin clasificar" sembrado por el sistema marcado como origen `system` y no puede eliminarlo ni renombrarlo.
2. **Given** un administrador en la sección, **When** crea un tipo personalizado con nombre y descripción opcional, **Then** queda disponible para asignar a proveedores del tenant y aparece marcado como "personalizado".
3. **Given** un tipo de proveedor existente con proveedores asociados, **When** el administrador intenta eliminarlo, **Then** el sistema impide la eliminación y ofrece "archivar"; los proveedores afectados deben reasignarse antes (manualmente o mediante reasignación masiva).
4. **Given** un tipo de proveedor sin proveedores asociados ni requisitos definidos, **When** el administrador lo elimina, **Then** desaparece del catálogo del tenant.
5. **Given** un tipo de proveedor "archivado", **When** un usuario intenta asignarlo a un proveedor nuevo, **Then** no aparece en el selector; los proveedores ya asignados a él se conservan con la etiqueta "tipo archivado" y un recordatorio para reclasificar.

---

### User Story 4 - Definir requisitos por tipo de proveedor (Priority: P1)

Un administrador entra al detalle de un `SupplierType` (p. ej. "Construcción") y selecciona qué tipos de documento debe presentar un proveedor de esa industria. Para cada documento puede usar la periodicidad canónica (heredada del `DocumentType`) o sobrescribirla con otra de la lista permitida.

**Why this priority**: Es el corazón funcional de la ampliación: sin asociaciones, los tipos de proveedor no aportan valor. P1.

**Independent Test**: En el tipo "Construcción" agregar 6 requisitos (opinión SAT, IMSS, INFONAVIT, ICSOE, SISUB, contrato); crear un proveedor de tipo "Construcción"; verificar que su detalle muestra esos 6 documentos como requeridos y ninguno más.

**Acceptance Scenarios**:

1. **Given** un tipo de proveedor "Construcción" sin requisitos, **When** el administrador agrega "Opinión SAT" sin override de periodicidad, **Then** queda guardado con periodicidad "mensual" heredada del `DocumentType` y los proveedores existentes de tipo "Construcción" pasan a exigirla (Faltante hasta que se cargue).
2. **Given** un requisito "Opinión SAT" en "Construcción" con periodicidad heredada (mensual), **When** el administrador la sobrescribe a "bimestral", **Then** los proveedores de tipo "Construcción" pasan a exigir la opinión SAT cada bimestre fiscal SAT/IMSS; los documentos previamente cargados con periodicidad mensual se reevalúan con la nueva regla.
3. **Given** un requisito existente, **When** el administrador lo elimina del tipo de proveedor, **Then** los proveedores de ese tipo dejan de exigirlo; los documentos previamente cargados se conservan en el histórico marcados como "requisito retirado".
4. **Given** un tipo de documento desactivado en el catálogo del tenant, **When** el administrador intenta asociarlo a un tipo de proveedor, **Then** el sistema lo impide y muestra "tipo desactivado; reactívalo primero en el catálogo de documentos".

---

### User Story 5 - Importar plantillas por industria (Priority: P2)

Un administrador abre el wizard "Importar plantilla por industria" y elige una o varias plantillas curadas (Construcción, Servicios profesionales, Transporte, Manufactura, Limpieza, Seguridad privada, Outsourcing/Staffing). Cada plantilla precarga un `SupplierType` con un nombre canónico y su lista de requisitos sugeridos. El administrador puede ajustar antes de confirmar.

**Why this priority**: Acelera dramáticamente el time-to-value en onboarding, pero NO es bloqueante: US3 + US4 permiten armar manualmente lo mismo. P2.

**Independent Test**: Importar la plantilla "Construcción"; verificar que aparece un nuevo `SupplierType` "Construcción" con 6-7 requisitos predefinidos y que el cliente puede editarlos antes o después de confirmar.

**Acceptance Scenarios**:

1. **Given** un administrador en la sección de tipos de proveedor, **When** abre el wizard y selecciona "Construcción", **Then** se le muestra una previsualización del tipo a crear y sus requisitos predefinidos (con periodicidad sugerida heredada del `DocumentType`), editable antes de confirmar.
2. **Given** una plantilla seleccionada que incluye un `DocumentType` actualmente desactivado en el tenant, **When** el administrador confirma la importación, **Then** el sistema avisa que ese requisito quedará inactivo hasta reactivar el tipo de documento y ofrece reactivarlo en el mismo flujo.
3. **Given** una plantilla ya importada previamente (tipo "Construcción" ya existe), **When** el administrador intenta volver a importarla, **Then** el sistema detecta el conflicto y ofrece (a) cancelar, (b) crear como "Construcción (2)" o (c) mergear los requisitos faltantes al tipo existente sin sobrescribir overrides previos.

---

### Edge Cases

**Tipos de documento (heredados del spec original)**

- ¿Qué pasa si un administrador intenta crear un tipo personalizado con el mismo nombre que un tipo del catálogo canónico? El sistema lo permite si los nombres difieren, pero advierte para evitar duplicados confusos.
- ¿Qué pasa si el nombre del tipo personalizado se repite dentro del mismo tenant? El sistema lo rechaza; el nombre debe ser único por tenant.
- ¿Qué pasa si se cambia la periodicidad de un tipo del catálogo canónico desde el tenant? No se permite directamente; sí se permite override por asociación a un `SupplierType` (FR-007 + FR-013 nuevo).
- ¿Quién puede tocar el catálogo? Solo el rol "administrador" del tenant; "gestor" y "consulta" tienen acceso de solo lectura.
- ¿Qué pasa cuando el equipo del producto agrega un nuevo tipo al catálogo canónico? Aparece automáticamente como inactivo por defecto en tenants existentes, notificado al admin; activo por defecto en tenants nuevos.

**Tipos de proveedor (nuevos)**

- ¿Qué pasa si se elimina "Sin clasificar"? No se permite en ningún caso (origen `system`). Solo se puede vaciar reasignando todos sus proveedores.
- ¿Qué pasa si un tipo de proveedor archivado tiene proveedores asignados? Los proveedores se mantienen pero se marcan visualmente como "tipo archivado, reclasificar"; no afectan al cálculo de cumplimiento agregado del tenant hasta reclasificarlos (o se cuentan como riesgo "Sin clasificar" — decisión deferred a `/speckit-clarify` post-feedback).
- ¿Qué pasa si se elimina un `DocumentType` (canónico desactivado o personalizado archivado) que está asociado como requisito a un tipo de proveedor? La asociación se mantiene pero queda marcada "tipo de documento inactivo"; en el cálculo del proveedor ese requisito no cuenta como "Faltante" mientras esté inactivo, y reaparece si el tipo se reactiva.
- ¿Qué pasa si la organización quiere cambiar la periodicidad sobreescrita en una asociación que ya tiene documentos cargados? El cambio aplica al recálculo del estado actual y futuro; los documentos pasados conservan su periodicidad efectiva original como dato histórico.

## Requirements *(mandatory)*

### Functional Requirements

**A. Catálogo de Tipos de Documento (heredado del spec original, sin cambios funcionales)**

- **FR-001**: El sistema DEBE exponer una sección de "Catálogos" accesible solo a usuarios con rol de administrador del tenant, con tres sub-secciones: "Tipos de documento", "Tipos de proveedor" y "Plantillas".
- **FR-002**: La sub-sección "Tipos de documento" DEBE mostrar dos vistas: tipos del **catálogo canónico** y tipos **personalizados** del tenant, diferenciados visualmente.
- **FR-003**: Un administrador DEBE poder activar o desactivar cualquier tipo del catálogo canónico dentro de su tenant. El cambio NO DEBE afectar a otros tenants.
- **FR-004**: Un administrador DEBE poder crear tipos personalizados con nombre (texto), periodicidad (mensual / bimestral / anual / sin vigencia) y descripción opcional. La periodicidad debe ser uno de los valores soportados.
- **FR-005**: El sistema DEBE garantizar unicidad del nombre de tipo de documento dentro del tenant (canónico + personalizado), rechazando duplicados exactos (insensible a mayúsculas/espacios al inicio o fin).
- **FR-006**: Un administrador DEBE poder editar nombre y descripción de un tipo personalizado. La periodicidad puede cambiarse pero aplica solo a cargas posteriores.
- **FR-007**: La periodicidad de los tipos del catálogo canónico NO DEBE ser editable globalmente desde el tenant; SÍ puede sobreescribirse al asociarlos a un `SupplierType` (ver FR-013).
- **FR-008**: Un administrador DEBE poder eliminar un tipo personalizado solo si no tiene documentos cargados ni asociaciones a tipos de proveedor; en caso contrario, ofrecer "archivar".
- **FR-009**: Al desactivar o archivar un tipo, los documentos previamente cargados a ese tipo DEBEN permanecer visibles en el detalle del proveedor con etiqueta "tipo inactivo / archivado", y DEBEN dejar de contar como requisitos activos.
- **FR-010**: Al reactivar un tipo previamente desactivado, los documentos cargados existentes DEBEN reincorporarse al cálculo de estado.
- **FR-011**: Todos los cambios al catálogo (activar/desactivar canónico, crear/editar/eliminar/archivar personalizado) DEBEN registrarse en la bitácora con usuario, acción, tipo afectado, fecha/hora y valores anterior/nuevo donde aplique.
- **FR-012**: Cuando el equipo del producto agregue un nuevo tipo al catálogo canónico, el sistema DEBE incorporarlo como **inactivo por defecto** en tenants existentes (con notificación al admin) y **activo** en tenants nuevos.

**B. Catálogo de Tipos de Proveedor (nuevo)**

- **FR-013**: El sistema DEBE auto-sembrar el `SupplierType` "Sin clasificar" (origen `system`) en cada tenant al crear la organización, con activos todos los `DocumentType` canónicos del catálogo del tenant como requisitos (heredando su periodicidad). Este tipo NO DEBE poder eliminarse, archivarse ni renombrarse.
- **FR-014**: Un administrador DEBE poder crear tipos de proveedor personalizados con nombre (texto, único por tenant), descripción opcional y estado inicial "activo".
- **FR-015**: Un administrador DEBE poder editar nombre y descripción de un tipo de proveedor personalizado.
- **FR-016**: Un administrador DEBE poder archivar un tipo de proveedor personalizado. Si tiene proveedores asignados, la acción se acompaña de un aviso: los proveedores deben reasignarse para que dejen de aparecer marcados como "tipo archivado".
- **FR-017**: Un administrador DEBE poder eliminar un tipo de proveedor personalizado solo si no tiene proveedores asociados ni requisitos definidos; en caso contrario, se ofrece archivar.
- **FR-018**: Todos los cambios al catálogo de tipos de proveedor DEBEN registrarse en bitácora (usuario, acción, tipo afectado, valores anterior/nuevo).

**C. Asociación Tipo de Proveedor ↔ Tipos de Documento (nuevo)**

- **FR-019**: Desde el detalle de un `SupplierType`, un administrador DEBE poder ver, agregar y eliminar requisitos: asociaciones a uno o más `DocumentType` activos del catálogo del tenant. Para cada requisito puede dejar `periodicity_override = null` (hereda del DocumentType) o seleccionar una periodicidad de la lista permitida.
- **FR-020**: Editar un requisito (agregar, quitar, override de periodicidad) DEBE recalcular inmediatamente el estado de cumplimiento de los proveedores afectados (los que tienen ese `SupplierType`) sin requerir acciones manuales adicionales.
- **FR-021**: NO DEBE permitirse asociar un `DocumentType` desactivado a un `SupplierType`. Si el tipo se desactiva después de crear la asociación, esta queda con bandera "tipo de documento inactivo" y no cuenta como "Faltante" hasta que el tipo se reactive.
- **FR-022**: Todos los cambios en asociaciones (crear, eliminar, override) DEBEN registrarse en bitácora.

**D. Plantillas por industria (nuevo)**

- **FR-023**: El sistema DEBE ofrecer un wizard "Importar plantilla por industria" con al menos 7 plantillas curadas por el equipo de producto: Construcción, Servicios profesionales, Transporte, Manufactura, Limpieza, Seguridad privada, Outsourcing/Staffing. Cada plantilla define un nombre canónico de `SupplierType` y una lista de requisitos sugeridos con periodicidad por defecto.
- **FR-024**: Al importar una plantilla, el sistema DEBE permitir editar el nombre, los requisitos y las periodicidades antes de confirmar.
- **FR-025**: Al importar una plantilla cuyo `SupplierType` con el mismo nombre ya existe en el tenant, el sistema DEBE ofrecer tres opciones: (a) cancelar, (b) crear con nombre alternativo, (c) mergear requisitos faltantes preservando overrides previos.
- **FR-026**: La importación de plantillas DEBE registrarse en bitácora indicando plantilla, tipo creado/actualizado y requisitos resultantes.

### Key Entities

- **Asociación Tipo-Tenant (DocumentType activo/inactivo por tenant)**: Vincula un tipo del catálogo canónico con una organización. Atributos: tipo canónico, tenant, activo, fecha último cambio, usuario.
- **Tipo Personalizado de Documento**: Tipo creado por el tenant. Atributos: nombre, periodicidad, descripción, estado (activo / archivado), tenant propietario.
- **Tipo de Proveedor (SupplierType)**: Industria del proveedor (p. ej. "Construcción"). Atributos: nombre, descripción, origen (`system` para "Sin clasificar" sembrado / `custom` para los creados por el tenant), estado (activo / archivado), tenant propietario.
- **Requisito por Tipo de Proveedor (SupplierTypeDocumentRequirement)**: Asociación entre `SupplierType` y `DocumentType`. Atributos: tipo de proveedor, tipo de documento, periodicidad efectiva (NULL = hereda; valor = override), activa, fecha de creación, usuario creador.
- **Plantilla por Industria (catálogo canónico maestro, fuera del tenant)**: Definida por el equipo de producto. Atributos: slug, nombre, descripción, lista de slugs de DocumentType + periodicidad sugerida. Inmutable desde la UI del tenant; importable como copia editable.
- Las entidades `DocumentType`, `Supplier`, `Document` y `AuditLog` se definen en spec 001 y son reutilizadas aquí.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un administrador puede desactivar tipos de documento no aplicables y crear su primer tipo personalizado en <3 minutos desde abrir la sección por primera vez.
- **SC-002**: Un administrador puede crear su primer tipo de proveedor + definir 5 requisitos en <5 minutos desde abrir la sección por primera vez.
- **SC-003**: Un administrador puede importar la plantilla "Construcción" y tener un `SupplierType` totalmente funcional asignable a proveedores en <60 segundos.
- **SC-004**: El catálogo del tenant A puede ser modificado (en cualquiera de los tres ejes) sin que ningún cambio aparezca en el tenant B, validado en pruebas automatizadas multi-tenant.
- **SC-005**: 100% de los documentos cargados antes de desactivar/archivar un tipo siguen recuperables y descargables después del cambio.
- **SC-006**: El indicador de cumplimiento agregado refleja correctamente los cambios de catálogo (cualquiera de los tres ejes) dentro del mismo día sin procesos manuales adicionales.
- **SC-007**: Cero cambios accidentales al catálogo canónico maestro de documentos ni a las plantillas canónicas de industria desde la UI del tenant.
- **SC-008**: 100% de las asociaciones que apuntan a `DocumentType` desactivados se manejan correctamente (no cuentan como Faltante, no se aceptan creaciones nuevas, reaparecen al reactivar el tipo), validado en pruebas automatizadas.

## Assumptions

- Solo el rol "administrador" del tenant puede modificar cualquier catálogo. Roles "gestor" y "consulta" tienen acceso de solo lectura sobre los tres ejes.
- El catálogo canónico maestro de documentos y las plantillas canónicas de industria los mantiene el equipo de producto fuera del MVP (migraciones / panel interno); este spec no cubre esa interfaz.
- Las periodicidades disponibles son las fijadas en el spec 001: mensual, bimestral, anual, sin vigencia. Periodicidades adicionales (trimestral, semestral) no se ofrecen en v1.
- Los tipos personalizados (documento y proveedor) y sus asociaciones existen solo a nivel tenant; no hay compartición entre organizaciones ni marketplace en v1.
- El número de plantillas canónicas por industria (7) es punto de partida; el equipo puede ampliarlo en releases posteriores sin requerir cambio de spec.
- La reasignación masiva de proveedores entre tipos (al archivar un tipo) se ofrece como flujo guiado, pero no es bloqueante para el archivado del tipo en sí (se permite archivar dejando proveedores marcados; el admin tiene tareas pendientes en el centro de notificaciones).
