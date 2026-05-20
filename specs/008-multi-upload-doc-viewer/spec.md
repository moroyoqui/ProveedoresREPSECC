# Feature Specification: Carga Múltiple de Archivos y Visualizador de Documentos

**Feature Branch**: `008-multi-upload-doc-viewer`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Quiero que actualices la especificación de este spec. que cuando le des clic para verificar y ya se encuentre un archivo arriba, no te lo descargue de manera automática, Sino que puedas visualizar el contenido cuando sea: PDF imagen o cualquier otro formato que pueda ser renderizado en el browser. Quiero que también te dé la opción para subir documentos adicionales siempre y cuando esté en estatus no validado"

**Extends**: [spec 006 — Vista de Cumplimiento Anual del Proveedor](../006-supplier-compliance-view/spec.md)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Subir múltiples archivos en una sola operación (Priority: P1)

El administrador de cumplimiento REPSE está revisando la cuadrícula de un proveedor y necesita cargar los comprobantes de un período. En lugar de tener que hacer clic en "Subir" una vez por cada archivo, selecciona todos los archivos del período desde su carpeta y los sube de una sola vez, viendo el progreso de cada uno individualmente.

**Why this priority**: Reducir la fricción en la carga de documentos es el cambio de mayor impacto en el flujo de trabajo diario; sin él el formulario de carga sigue siendo un cuello de botella cuando hay múltiples comprobantes por período.

**Independent Test**: Se puede testear abriendo el diálogo de carga para cualquier celda roja, seleccionando varios archivos a la vez (mínimo 3) desde el sistema de archivos, confirmando la carga y verificando que todos los archivos quedan registrados bajo el mismo proveedor, tipo de documento y período.

**Acceptance Scenarios**:

1. **Given** el diálogo de carga de documentos está abierto para una celda, **When** el usuario hace clic en el área de selección de archivos, **Then** el explorador de archivos del sistema operativo permite seleccionar uno o más archivos simultáneamente.
2. **Given** el usuario seleccionó 3 archivos, **When** confirma la carga, **Then** los 3 archivos se suben de forma independiente y cada uno muestra su propio indicador de progreso.
3. **Given** algunos archivos de la selección fallan al subirse, **When** termina la operación, **Then** el sistema muestra cuántos se subieron correctamente y cuántos fallaron, con la opción de reintentar solo los fallidos.
4. **Given** el usuario seleccionó al menos un archivo, **When** todos terminan de subirse con éxito, **Then** el diálogo se cierra, la cuadrícula refleja el nuevo estado y todos los archivos quedan asociados al período y tipo de documento correspondientes.
5. **Given** el usuario no ha seleccionado ningún archivo, **When** intenta confirmar la carga, **Then** el botón de confirmar permanece deshabilitado y se muestra un mensaje que pide seleccionar al menos un archivo.

---

### User Story 2 - Visualizar documentos subidos sin descarga automática (Priority: P1)

El administrador hace clic en una esfera de la cuadrícula que tiene documentos cargados (verde o amarilla) para revisar esos archivos y verificar su autenticidad. En lugar de que el sistema inicie una descarga automática del archivo, se abre un panel o modal donde puede ver el contenido directamente en el navegador si el formato lo permite (PDF, imágenes u otros formatos renderizables), y solo descarga el archivo si él mismo lo solicita explícitamente.

**Why this priority**: La verificación de autenticidad de documentos es el propósito central del cumplimiento REPSE. Descargar el archivo automáticamente interrumpe el flujo de revisión y obliga al usuario a salir de la aplicación; mostrar el contenido en línea convierte la cuadrícula en punto de acceso completo al acervo documental sin fricción.

**Independent Test**: Se puede testear haciendo clic en una esfera verde de un proveedor que ya tiene al menos un PDF o imagen cargada, verificando que el visor se abre con el contenido del archivo renderizado directamente —sin iniciar ninguna descarga— y que el botón de descarga es visible pero requiere clic explícito del usuario para activarse.

**Acceptance Scenarios**:

1. **Given** una celda con al menos un documento subido (esfera verde o amarilla), **When** el usuario hace clic en la esfera para verificar, **Then** se abre el visualizador de documentos y el sistema NO inicia ninguna descarga automática.
2. **Given** el visualizador está abierto con un PDF seleccionado, **When** se muestra la vista del archivo, **Then** el contenido del PDF se renderiza directamente dentro del panel sin necesidad de descargarlo.
3. **Given** el visualizador está abierto con una imagen (JPG, PNG, GIF, WebP, SVG), **When** se muestra la vista del archivo, **Then** la imagen se muestra directamente dentro del panel a tamaño completo o ajustada al espacio disponible.
4. **Given** el visualizador está abierto con cualquier formato renderizable por el navegador (p. ej. texto plano, HTML), **When** se muestra la vista del archivo, **Then** el contenido se renderiza en línea dentro del panel.
5. **Given** el visualizador está abierto, **When** el usuario hace clic en el botón "Descargar" junto a un archivo, **Then** el archivo se descarga al equipo del usuario manteniendo su nombre y extensión originales; este es el único momento en que ocurre una descarga.
6. **Given** el panel de documentos está abierto y hay más de un archivo, **When** el usuario navega entre archivos (anterior / siguiente), **Then** la vista previa cambia sin cerrar ni recargar el panel y sin iniciar descarga alguna.
7. **Given** una celda roja (sin documentos), **When** el usuario hace clic en la esfera, **Then** se abre el diálogo de carga (comportamiento ya definido en spec 006 FR-009), no el visualizador.
8. **Given** el visualizador está abierto, **When** el usuario pulsa Escape o hace clic fuera del panel, **Then** el panel se cierra y la cuadrícula vuelve a ser interactiva.

---

### User Story 3 - Agregar documentos adicionales a un período no validado (Priority: P1)

El administrador está revisando los documentos de un período en el visualizador y se da cuenta de que falta un comprobante adicional. Como el período aún no ha sido marcado como validado, puede agregar más archivos directamente desde el mismo visualizador sin tener que cerrar el panel y buscar otra ruta de acceso. Si el período ya fue validado, la opción de agregar documentos no aparece.

**Why this priority**: Permitir agregar documentos adicionales a entradas no validadas elimina un flujo de trabajo complicado (cerrar el visualizador, navegar a una celda roja, volver a subir) y cierra la brecha entre "revisar" y "completar" el acervo documental de un período, reduciendo errores de omisión.

**Independent Test**: Se puede testear abriendo el visualizador de una celda con documentos y estado "no validado" y verificando que aparece un botón o área de carga adicional; luego subir un archivo nuevo y confirmar que aparece en la lista del visualizador sin cerrarlo. Repetir con una celda validada y verificar que el botón de carga adicional NO aparece.

**Acceptance Scenarios**:

1. **Given** el visualizador está abierto para una celda con estado no validado, **When** el usuario ve la lista de documentos, **Then** aparece un botón o área de acción claramente identificada como "Agregar documento" o equivalente.
2. **Given** el botón "Agregar documento" está visible, **When** el usuario hace clic en él, **Then** puede seleccionar uno o más archivos adicionales desde el sistema de archivos sin cerrar el visualizador.
3. **Given** el usuario seleccionó archivos adicionales, **When** confirma la carga, **Then** los nuevos archivos se suben y aparecen en la lista del visualizador manteniendo la sesión de revisión abierta.
4. **Given** el visualizador está abierto para una celda con estado validado, **When** el usuario ve la lista de documentos, **Then** el botón de "Agregar documento" NO aparece y la vista es solo de lectura y descarga.
5. **Given** el usuario está en proceso de agregar documentos adicionales y uno falla, **When** termina la operación parcial, **Then** el sistema informa sobre el archivo fallido y permite reintentarlo sin afectar los documentos ya existentes en el período.

---

### User Story 4 - Identificar el número de archivos subidos por celda (Priority: P2)

Para que el usuario sepa de un vistazo cuántos archivos tiene registrados en un período, la esfera muestra un indicador del número de documentos asociados cuando hay más de uno.

**Why this priority**: Mejora la legibilidad de la cuadrícula sin alterar la lógica de colores existente; puede implementarse de forma independiente una vez que US1, US2 y US3 estén activas.

**Independent Test**: Se puede testear subiendo dos archivos para un período y verificando que la esfera correspondiente muestra el contador "2" o un indicador equivalente.

**Acceptance Scenarios**:

1. **Given** una celda con exactamente un archivo subido, **When** se muestra la cuadrícula, **Then** la esfera no muestra contador adicional (comportamiento limpio).
2. **Given** una celda con dos o más archivos subidos, **When** se muestra la cuadrícula, **Then** la esfera muestra un pequeño indicador numérico con el conteo de archivos.
3. **Given** el tooltip de la esfera, **When** el usuario pasa el cursor sobre una celda con múltiples archivos, **Then** el tooltip incluye el número total de archivos además del estado de cumplimiento.

---

### Edge Cases

- ¿Qué pasa si el usuario intenta subir un archivo de tipo no permitido (p. ej. `.exe`)? → El sistema rechaza el archivo antes de iniciar la transferencia y muestra un mensaje con los tipos permitidos.
- ¿Qué pasa si uno de los archivos supera el tamaño máximo permitido? → Ese archivo se rechaza individualmente; los demás de la selección continúan subiéndose.
- ¿Qué pasa si la conexión se interrumpe durante una carga múltiple? → Los archivos ya subidos se conservan; los pendientes se marcan como fallidos con opción de reintento.
- ¿Qué pasa si el usuario abre el visualizador y otro usuario sube un nuevo archivo al mismo período al mismo tiempo? → El visualizador muestra los archivos al momento en que se abrió; un botón de "Actualizar" permite refrescar la lista sin cerrar el panel.
- ¿Qué pasa si el formato del archivo no admite vista previa en el navegador (p. ej. `.xlsx`, `.docx`)? → El panel muestra el nombre del archivo, su tamaño y solo el botón de descarga, sin área de previsualización; nunca se inicia una descarga automática.
- ¿Qué pasa si hay decenas de archivos asociados a un período? → La lista del visualizador tiene scroll; no se pagina.
- ¿Qué pasa si el usuario intenta agregar documentos a un período ya validado? → El botón de carga adicional no está disponible; el visualizador muestra una nota indicando que el período está validado y no admite cambios.
- ¿Qué pasa si el PDF es muy extenso (más de 100 páginas)? → El navegador renderiza el PDF completo con scroll propio; el sistema no limita la longitud del documento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir seleccionar y subir múltiples archivos en una sola operación desde el diálogo de carga de documentos.
- **FR-002**: Cada archivo de una carga múltiple DEBE procesarse de forma independiente, mostrando su propio estado de progreso (en espera, subiendo, completado, error).
- **FR-003**: Al finalizar una carga múltiple parcialmente fallida, el sistema DEBE informar el conteo de archivos exitosos y fallidos, y ofrecer la opción de reintentar únicamente los fallidos.
- **FR-004**: Al hacer clic en una esfera con documentos asociados (verde o amarilla), el sistema DEBE abrir el visualizador de documentos sin iniciar ninguna descarga automática de archivos.
- **FR-005**: El visualizador DEBE listar todos los archivos asociados al período y tipo de documento de la celda seleccionada, mostrando nombre, tamaño y fecha de carga de cada uno.
- **FR-006**: El visualizador DEBE renderizar el contenido del archivo directamente dentro del panel para todos los formatos que el navegador puede mostrar de forma nativa: PDF, JPG, PNG, GIF, WebP, SVG y texto plano, sin requerir descarga previa ni abrir una ventana nueva.
- **FR-007**: Para archivos sin soporte de vista previa nativa en el navegador (p. ej. `.xlsx`, `.docx`, `.zip`), el visualizador DEBE mostrar un ícono representativo del tipo de archivo y un botón de descarga prominente, nunca iniciar una descarga automática.
- **FR-008**: El visualizador DEBE ofrecer un botón de descarga individual y explícito para cada archivo de la lista; la descarga solo se inicia cuando el usuario hace clic en dicho botón.
- **FR-009**: El visualizador DEBE permitir navegar entre archivos (anterior / siguiente) cuando hay más de uno, actualizando la vista previa sin cerrar ni recargar el panel y sin iniciar descarga alguna.
- **FR-010**: Cuando una celda tiene más de un archivo, la esfera DEBE mostrar un indicador numérico con el conteo de archivos.
- **FR-011**: El sistema DEBE validar el tipo y tamaño de cada archivo antes de iniciar la transferencia, rechazando los que no cumplan los criterios y permitiendo continuar con los demás.
- **FR-012**: El visualizador DEBE cerrarse al presionar Escape o hacer clic fuera del área del panel, devolviendo el foco a la cuadrícula.
- **FR-013**: Cuando el visualizador está abierto para una celda con estado no validado, DEBE mostrar una opción para agregar documentos adicionales al período sin necesidad de cerrar el visualizador.
- **FR-014**: La opción de agregar documentos adicionales (FR-013) DEBE estar oculta o deshabilitada cuando la celda tiene estado validado; en ese estado el visualizador opera en modo solo lectura y descarga.
- **FR-015**: Al agregar documentos adicionales desde el visualizador, el sistema DEBE subirlos siguiendo las mismas reglas de validación de tipo y tamaño que FR-011, y mostrarlos en la lista del visualizador al terminar sin cerrar el panel.

### Key Entities

- **Carga de documentos**: Operación que asocia uno o más archivos físicos a un proveedor, tipo de documento y período. Cada archivo es un ítem independiente con su propio estado de transferencia.
- **Archivo de documento**: Un fichero individual subido como parte de una carga; tiene nombre, tipo MIME, tamaño y fecha de carga. Puede ser previsualizeable directamente en el navegador o solo descargable según su tipo MIME.
- **Visualizador de documentos**: Componente de interfaz que abre el acervo de archivos de una celda específica; permite previsualización en línea, navegación y descarga explícita. En celdas no validadas también expone la opción de agregar documentos adicionales.
- **Estado de validación**: Condición de una celda que indica si los documentos del período han sido revisados y aceptados por un supervisor. Determina si el visualizador muestra la opción de carga adicional.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede cargar un lote de 5 archivos para un período en menos de la mitad del tiempo que le tomaría subirlos de uno en uno.
- **SC-002**: El 100% de los archivos de una carga múltiple que superan validación de tipo y tamaño quedan registrados correctamente bajo el período y tipo de documento seleccionados.
- **SC-003**: El administrador puede abrir el visualizador, revisar y descargar cualquier documento de una celda en menos de 30 segundos desde que hace clic en la esfera.
- **SC-004**: La vista previa integrada carga y muestra archivos PDF e imágenes en menos de 3 segundos en condiciones normales de red interna, sin que el sistema inicie ninguna descarga en ningún momento del proceso.
- **SC-005**: Tras una carga fallida parcial, el usuario puede identificar qué archivos fallaron y reintentarlos sin tener que volver a seleccionar los archivos exitosos.
- **SC-006**: Un administrador puede agregar un documento adicional a un período no validado desde el visualizador en menos de 60 segundos, sin perder el contexto de revisión (el panel permanece abierto).

## Assumptions

- Los tipos de archivo permitidos y el tamaño máximo por archivo ya están definidos en la configuración del sistema (spec 001); esta feature los consume sin modificarlos.
- El visualizador de documentos se implementa como modal o panel lateral dentro de la pantalla de cumplimiento (no como ventana separada ni nueva ruta), ya que mantener el contexto de la cuadrícula es prioritario para el flujo de verificación.
- La autenticación y autorización existentes aplican sin cambios: solo usuarios con rol administrador o supervisor de cumplimiento pueden acceder a la pantalla y al visualizador.
- Los archivos ya subidos previamente (un solo archivo por celda) seguirán siendo accesibles desde el visualizador sin necesidad de migración de datos.
- La vista previa de archivos utiliza las capacidades nativas del navegador; no se requiere un servidor de renderizado de documentos adicional.
- No se contempla edición, anotación ni firma digital de documentos dentro del visualizador en esta versión; es exclusivamente de lectura, descarga y carga adicional.
- Los archivos sin periodicidad mensual (documentos de entrega única de spec 006) también podrán visualizarse y recibir documentos adicionales (si no están validados) con el mismo componente.
- El estado "no validado" incluye todos los estados previos a la validación formal por supervisor (p. ej. "pendiente", "en revisión"); el estado "validado" es el único que bloquea la carga adicional.
