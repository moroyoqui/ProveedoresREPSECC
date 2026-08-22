# Feature Specification: Unificación de "Validado" y "Verificado"

**Feature Branch**: `017-unify-verification`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "necesito modificar el comportamiento y que quede en el spec documentado con speckit, validado y verificado debe ser lo mismo, no separado"

> **Origen**: se detectó en producción de desarrollo que el documento "Cédula cuota IMSS" de julio 2026 del proveedor Prov1 aparecía como **no verificado** en `/documents` aunque su celda de cumplimiento **sí estaba validada** desde la rejilla del proveedor. No era un fallo de la pantalla: son dos marcas distintas que el sistema nunca sincronizó. Esta feature las convierte en una sola.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Una sola marca, coherente en toda la aplicación (Priority: P1)

Un gestor revisa la documentación de un proveedor desde la rejilla de cumplimiento y da por buena la evidencia de un tipo de documento y período. Al abrir después la pantalla de documentos, ese documento aparece revisado, con el nombre de quien lo revisó y la fecha. No existe ningún camino por el que la rejilla diga una cosa y la pantalla de documentos diga la contraria.

**Why this priority**: es el problema que originó la petición. Mientras las dos marcas puedan divergir, quien consulta no sabe cuál creer y la evidencia pierde valor.

**Independent Test**: dar por revisada una celda desde la rejilla del proveedor, abrir el documento de esa celda en la pantalla de documentos y comprobar que figura como revisado, con autor y fecha; y a la inversa, revisar un documento desde su detalle y comprobar que la celda correspondiente aparece revisada en la rejilla.

**Acceptance Scenarios**:

1. **Given** un gestor ante una celda con documento vigente sin revisar, **When** la da por revisada desde la rejilla, **Then** el documento vigente de esa celda queda marcado como revisado, con su nombre y la fecha, y la celda se muestra revisada.
2. **Given** ese mismo documento, **When** el gestor lo abre en la pantalla de documentos, **Then** lo ve marcado como revisado con el mismo autor y la misma fecha que muestra la rejilla.
3. **Given** un gestor que marca un documento como revisado desde su detalle, **When** vuelve a la rejilla de cumplimiento del proveedor, **Then** la celda de ese tipo y período aparece revisada sin necesidad de repetir la acción.
4. **Given** una celda con varios documentos, **When** se da por revisada, **Then** queda revisado el documento vigente de la celda y el estado mostrado es único y consistente en ambas pantallas.

---

### User Story 2 - Retirar la revisión (Priority: P1)

Quien revisó un documento por error, o descubre que la evidencia no era válida, puede retirar la revisión desde cualquiera de las dos pantallas. La celda deja de figurar como revisada en el mismo acto.

**Why this priority**: hoy la validación de celda **no tiene reverso**: una vez dada por buena, no hay forma de deshacerla. Unificar sin resolver esto dejaría el sistema en un estado peor, porque la marca de celda pasaría a ser irreversible también para el documento.

**Independent Test**: retirar la revisión de un documento y comprobar que tanto la pantalla de documentos como la rejilla del proveedor dejan de mostrarlo revisado.

**Acceptance Scenarios**:

1. **Given** un documento revisado, **When** un gestor o un administrador retira la revisión, **Then** el documento y la celda dejan de figurar como revisados en ambas pantallas.
2. **Given** un usuario con rol de solo lectura, **When** consulta un documento revisado, **Then** no se le ofrece retirar la revisión.
3. **Given** una revisión retirada, **When** se consulta el historial, **Then** consta quién la retiró y cuándo, sin borrar el registro de la revisión previa.

---

### User Story 3 - El histórico queda coherente (Priority: P2)

Un administrador que revisa el trabajo acumulado no encuentra celdas dadas por buenas cuyos documentos figuren sin revisar. Los casos que hoy están divergentes quedan alineados, conservando quién y cuándo se dio por buena cada celda.

**Why this priority**: sin esto, la regla nueva conviviría con un histórico incoherente durante un tiempo indefinido, y el problema reportado seguiría visible en los datos que ya existen.

**Independent Test**: comprobar, sobre los datos ya existentes, que toda celda dada por revisada tiene su documento vigente marcado como revisado, con la autoría y fecha de la revisión original.

**Acceptance Scenarios**:

1. **Given** una celda dada por revisada antes de este cambio cuyo documento vigente figura sin revisar, **When** se aplica el cambio, **Then** ese documento queda marcado como revisado conservando el autor y la fecha de la revisión de la celda.
2. **Given** un documento revisado antes del cambio cuya celda no figuraba revisada, **When** se aplica el cambio, **Then** la celda pasa a mostrarse revisada sin alterar la autoría ni la fecha del documento.
3. **Given** el histórico ya alineado, **When** se consulta cualquier celda revisada, **Then** el autor y la fecha que muestra coinciden con los del documento.

---

### Edge Cases

- **Celda sin documento vigente**: no se puede dar por revisada — no hay evidencia que respaldar. El sistema lo impide con un motivo claro en lugar de crear una marca huérfana.
- **Se sube una versión nueva sobre una celda ya revisada**: la revisión no se hereda. La evidencia cambió, así que la celda vuelve a figurar pendiente de revisión hasta que alguien revise la versión nueva.
- **Se elimina el documento revisado**: la celda deja de figurar revisada; si había una versión anterior que pasa a ser la vigente, el estado se recalcula sobre ella.
- **Celda con varios documentos vigentes simultáneos**: la marca sigue al documento vigente de la celda; si el sistema admite más de uno, el criterio de qué documento porta la marca debe ser único y estable, no depender del orden de consulta.
- **Dos usuarios revisan a la vez** la misma celda desde pantallas distintas: el resultado es una sola marca, sin duplicados ni error visible.
- **Revisión retirada sobre celda con envío del proveedor pendiente**: el estado de la celda vuelve a pendiente de revisión sin afectar al envío del proveedor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST tratar "validado" y "verificado" como un **único concepto**, con un solo estado, un solo autor y una sola fecha por evidencia.
- **FR-002**: El estado MUST residir en el **documento**; el estado de la celda de cumplimiento MUST derivarse del documento vigente de esa celda, en lugar de almacenarse por separado.
- **FR-003**: Dar por revisada una celda desde la rejilla MUST marcar como revisado el documento vigente de esa celda, registrando autor y fecha.
- **FR-004**: Marcar un documento como revisado desde su detalle MUST hacer que la celda correspondiente figure revisada, sin ninguna acción adicional del usuario.
- **FR-005**: El sistema MUST impedir dar por revisada una celda que no tenga documento vigente, indicando el motivo.
- **FR-006**: El sistema MUST permitir retirar la revisión desde ambas pantallas, y MUST reflejar el cambio en las dos de forma inmediata.
- **FR-007**: Tanto marcar como retirar la revisión MUST estar permitido a los roles administrador y gestor, y MUST negarse a los roles de solo lectura y de proveedor.
- **FR-008**: El sistema MUST registrar en el historial de auditoría tanto la revisión como su retirada, con autor y fecha, cualquiera que sea la pantalla desde la que se ejecuten.
- **FR-009**: Al subir una versión nueva de un documento sobre una celda revisada, el sistema MUST dejar la celda como pendiente de revisión.
- **FR-010**: El sistema MUST alinear los datos existentes: toda celda dada por revisada antes de este cambio MUST quedar reflejada como revisión de su documento vigente, conservando el autor y la fecha originales.
- **FR-011**: Las pantallas que hoy hablan de "validar" y de "verificar" MUST usar un **mismo término** en toda la aplicación, para que el usuario no perciba dos acciones distintas.
- **FR-012**: El sistema MUST conservar la nota opcional que hoy acompaña a la verificación del documento, disponible también cuando la revisión se hace desde la rejilla.
- **FR-013**: Las reglas que hoy dependen del estado de la celda —en particular el bloqueo del borrado de documentos y del envío del proveedor— MUST seguir comportándose igual, leyendo ahora el estado unificado.

### Key Entities

- **Documento**: evidencia cargada para un proveedor, tipo y período. Pasa a ser el **único portador** del estado de revisión, con su autor, fecha y nota.
- **Celda de cumplimiento**: cruce de proveedor, tipo de documento y período. Su estado de revisión pasa a ser **derivado**, no almacenado.
- **Registro de validación de celda**: deja de ser fuente de verdad. Su contenido histórico se traslada a los documentos correspondientes.
- **Registro de auditoría**: recoge revisión y retirada con autor y fecha, con independencia de la pantalla de origen.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cero discrepancias entre lo que muestra la rejilla de cumplimiento y lo que muestra la pantalla de documentos sobre una misma evidencia.
- **SC-002**: El 100% de las celdas dadas por revisadas —incluidas las anteriores a este cambio— tienen su documento vigente marcado como revisado, con el mismo autor y fecha.
- **SC-003**: Toda revisión y toda retirada de revisión quedan consultables en el historial con autor y fecha, sea cual sea la pantalla desde la que se hicieron.
- **SC-004**: Un usuario que revisa evidencia realiza **una sola acción** para dejarla dada por buena, en lugar de dos acciones en dos pantallas distintas.
- **SC-005**: Las consultas de la rejilla de cumplimiento no se vuelven más lentas de forma perceptible al pasar a derivar el estado.

## Assumptions

- **El documento manda**: decisión tomada explícitamente al especificar. El documento es la unidad de evidencia y ya cuenta con autoría, fecha, nota, auditoría y reverso; la celda hereda su estado. La alternativa —que mandara la celda— obligaba a dotar a la celda de todo eso desde cero y a perder el detalle por documento.
- **El histórico se migra y se alinea**: decisión tomada explícitamente al especificar. Se prefiere una migración única a convivir indefinidamente con datos divergentes como el caso que originó la petición.
- **Retirar la revisión queda permitido a administrador y gestor**: decisión tomada explícitamente al especificar. Supone un **cambio respecto al comportamiento actual**, donde retirar la verificación de un documento es exclusivo del administrador. Se acepta a cambio de que ambas pantallas se comporten igual y de que el gestor pueda deshacer su propio error.
- Se asume que la celda tiene un documento vigente identificable de forma única; si la aplicación admitiera varios simultáneos, el criterio de cuál porta la marca debe fijarse en el plan.
- El término único a usar en la interfaz se decidirá en el plan; la especificación sólo exige que sea **uno solo** en toda la aplicación (FR-011).
- Queda fuera de alcance: revisar en bloque varias celdas a la vez, flujos de aprobación por varias personas, y notificar al proveedor cuando su evidencia se da por buena.
