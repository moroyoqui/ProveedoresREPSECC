# Feature Specification: Borrado de Documentos Propios en el Back-Office

**Feature Branch**: `016-own-document-delete`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Dentro del backend, Poner un botón de borrado Para aquellos documentos que haya subido él mismo"

> **Nota de alcance**: Esta feature cubre el **back-office administrativo** (la aplicación interna que usan admin, gestor y consultor), no el portal del proveedor. El proveedor ya cuenta con su propio borrado, especificado en [013-portal-upload-separation](../013-portal-upload-separation/spec.md), y su comportamiento no se modifica aquí.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Corregir una carga equivocada propia (Priority: P1)

Un gestor sube un documento a la ficha de un proveedor y, al revisarlo, advierte que se equivocó de archivo, de período o de proveedor. Desde la misma vista donde ve el documento encuentra un control de borrado que le permite eliminar esa carga sin depender de un administrador, siempre que el documento siga dentro de la ventana de corrección y nadie lo haya validado todavía.

**Why this priority**: Es el objetivo central de la petición. Sin él, cualquier carga equivocada obliga a escalar a un administrador, lo que bloquea el trabajo cotidiano de quien carga la documentación.

**Independent Test**: Un gestor autenticado sube un documento, lo localiza en la vista de documentos y usa el control de borrado; el documento desaparece del listado y la celda de cumplimiento del proveedor vuelve al estado que tenía antes de la carga.

**Acceptance Scenarios**:

1. **Given** un gestor autenticado que subió un documento hace menos de la ventana de corrección y la celda no ha sido validada, **When** abre la vista de ese documento, **Then** ve un control de borrado disponible.
2. **Given** ese mismo gestor con el control de borrado a la vista, **When** lo activa y confirma la acción, **Then** el documento deja de aparecer en el listado y la celda de cumplimiento del proveedor recalcula su estado.
3. **Given** el gestor activó el control de borrado, **When** ve la confirmación, **Then** la confirmación identifica sin ambigüedad qué documento se eliminará (proveedor, tipo de documento y período) y advierte que la acción no se puede deshacer.
4. **Given** el gestor cancela la confirmación, **When** vuelve al listado, **Then** el documento sigue presente y sin cambios.

---

### User Story 2 - No poder borrar lo ajeno (Priority: P1)

Un gestor consulta un documento que subió otra persona. El control de borrado no aparece, de modo que no puede eliminar el trabajo de un compañero ni por descuido ni deliberadamente.

**Why this priority**: Es la contraparte inseparable de la historia 1: sin esta restricción la funcionalidad abre un riesgo de pérdida de evidencia. Se implementa y prueba junto con el permiso, no después.

**Independent Test**: Con dos usuarios distintos, cargar un documento con el primero y verificar con el segundo que la vista de ese documento no ofrece control de borrado y que un intento directo de eliminarlo es rechazado.

**Acceptance Scenarios**:

1. **Given** un gestor autenticado ante un documento subido por otro usuario, **When** abre la vista del documento, **Then** no se muestra ningún control de borrado.
2. **Given** un gestor que intenta eliminar un documento ajeno saltándose la interfaz, **When** se procesa la petición, **Then** el sistema la rechaza por falta de permiso y el documento permanece intacto.
3. **Given** un consultor (rol de solo lectura) ante cualquier documento, incluso uno que figure a su nombre, **When** abre la vista del documento, **Then** no se muestra ningún control de borrado.

---

### User Story 3 - Rastro de auditoría del borrado (Priority: P2)

Un administrador que revisa el historial de cumplimiento de un proveedor necesita saber que un documento existió y fue eliminado, por quién y cuándo, para que el borrado propio no cree huecos inexplicables en la evidencia.

**Why this priority**: El valor principal ya se entrega con las historias 1 y 2; el rastro es lo que hace la funcionalidad aceptable para auditoría, pero no bloquea el uso diario.

**Independent Test**: Borrar un documento propio y verificar que el historial del proveedor —o del tipo de documento y período afectados— muestra la eliminación con autor y fecha.

**Acceptance Scenarios**:

1. **Given** un documento eliminado por su autor, **When** un administrador consulta el historial de esa celda de cumplimiento, **Then** ve un registro de la eliminación con el nombre de quien la ejecutó y la fecha y hora.
2. **Given** un documento eliminado, **When** cualquier usuario intenta descargarlo desde un enlace previo, **Then** el sistema responde que ya no está disponible en lugar de entregar el archivo.

---

### Edge Cases

- **Documento fuera de la ventana de corrección**: pasado el plazo, el control de borrado deja de ofrecerse y un intento directo se rechaza indicando que la ventana expiró.
- **Celda ya enviada a validación o validada**: si el documento respalda una celda que el proveedor envió a validación o que ya fue validada, el borrado se rechaza para no invalidar una revisión en curso o concluida.
- **Documento ya verificado por un revisor**: no se puede borrar; primero hay que retirar la verificación.
- **Documento que reemplazó a una versión anterior**: al eliminarlo, la versión previa vuelve a ser la vigente y el estado de la celda se recalcula sobre ella, no sobre un vacío.
- **Doble confirmación o doble clic**: eliminar dos veces el mismo documento no produce error visible para el usuario ni efectos duplicados en el historial.
- **Documento eliminado mientras otro usuario lo tiene abierto**: al intentar operar sobre él, el segundo usuario recibe un aviso de que el documento ya no existe en lugar de un fallo inesperado.
- **Autor dado de baja**: si el usuario que subió el documento fue deshabilitado, el documento deja de tener quien pueda borrarlo por esta vía; sólo un administrador puede eliminarlo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ofrecer, en la vista de documentos del back-office, un control de borrado sobre cada documento cuyo autor de carga sea el usuario autenticado.
- **FR-002**: El sistema MUST ocultar ese control en todo documento cuyo autor de carga sea otro usuario, sin perjuicio de la facultad que los administradores ya tienen de eliminar cualquier documento.
- **FR-003**: El sistema MUST exigir una confirmación explícita antes de eliminar, indicando el proveedor, el tipo de documento y el período afectados, y advirtiendo que la acción es irreversible.
- **FR-004**: El sistema MUST rechazar toda solicitud de borrado de un documento ajeno, aunque llegue por fuera de la interfaz, y MUST dejar el documento intacto.
- **FR-005**: El sistema MUST permitir el borrado propio únicamente dentro de la misma ventana de corrección configurada que ya rige la eliminación de documentos en el back-office, y MUST rechazarlo con un mensaje comprensible una vez expirada.
- **FR-006**: El sistema MUST rechazar el borrado cuando el documento esté verificado, o cuando la celda de cumplimiento asociada haya sido enviada a validación por el proveedor o ya validada, explicando el motivo del rechazo.
- **FR-007**: El sistema MUST negar el borrado a los usuarios con rol de solo lectura, con independencia de quién figure como autor de carga.
- **FR-008**: El sistema MUST recalcular el estado de cumplimiento del proveedor tras un borrado, restituyendo como vigente la versión anterior del mismo tipo y período cuando exista.
- **FR-009**: El sistema MUST registrar cada borrado en el historial de auditoría con el autor, la fecha y hora, y el documento afectado, de modo que la eliminación sea consultable después.
- **FR-010**: El sistema MUST impedir el acceso al archivo eliminado desde enlaces de descarga emitidos antes del borrado.
- **FR-011**: El sistema MUST confirmar visualmente el resultado del borrado y actualizar el listado sin exigir al usuario que recargue la pantalla.

### Key Entities

- **Documento**: evidencia cargada para un proveedor, un tipo de documento y un período. Conserva quién lo subió y cuándo, si es la versión vigente, si está verificado y si fue eliminado.
- **Usuario del back-office**: persona autenticada con un rol que determina qué puede hacer; su identidad es la que se compara con el autor de carga del documento.
- **Celda de cumplimiento**: cruce de proveedor, tipo de documento y período cuyo estado depende del documento vigente y condiciona si el borrado está permitido.
- **Registro de auditoría**: asiento inmutable de cada acción relevante sobre un documento, incluida su eliminación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Quien sube un documento por error puede corregirlo por su cuenta en menos de 30 segundos desde que lo detecta, sin intervención de un administrador.
- **SC-002**: El 100% de los intentos de eliminar un documento ajeno son rechazados y dejan el documento intacto.
- **SC-003**: El 100% de los borrados quedan reflejados en el historial con autor y fecha consultables.
- **SC-004**: Las solicitudes de eliminación dirigidas a administradores por cargas equivocadas se reducen a cero para los documentos que están dentro de la ventana de corrección.
- **SC-005**: Ningún borrado deja la ficha del proveedor en un estado de cumplimiento incoherente: tras la operación, la celda refleja la versión anterior o la ausencia de documento.

## Assumptions

- "Backend" en la petición se refiere al **back-office administrativo**, no al portal del proveedor ni a la capa de servicios: la petición habla de un "botón", es decir, de la interfaz interna. El portal del proveedor ya resuelve este caso por separado.
- "Él mismo" se refiere al **usuario autenticado** comparado con el autor de la carga del documento, no al proveedor como empresa.
- Los administradores **conservan** su facultad actual de eliminar cualquier documento; esta feature amplía la capacidad a quien carga documentos sin ser administrador, restringida a lo propio.
- Se reutiliza la **ventana de corrección ya configurada** para el borrado en el back-office, en lugar de introducir un plazo distinto, para no tener dos reglas de caducidad conviviendo.
- El borrado mantiene el comportamiento actual del sistema: el archivo se retira del almacenamiento y el registro queda marcado como eliminado a efectos de auditoría, en lugar de desaparecer sin rastro.
- La restricción sobre celdas enviadas a validación o ya validadas se alinea con la regla que ya se aplica al proveedor, por coherencia entre ambas experiencias.
- No forma parte del alcance: recuperar o restaurar documentos eliminados, el borrado masivo de varios documentos a la vez, ni notificar al proveedor de la eliminación.
