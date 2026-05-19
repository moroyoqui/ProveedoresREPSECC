# Feature Specification: Refresco del Grid y Leyenda de Colores

**Feature Branch**: `007-grid-refresh-color-legend`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Una vez que subas un documento de cierta vigencia, Quiero que se refresque el grid, Generalmente, quiero que aparezca un recuadro o lista, que indique los códigos de los colores y qué significa cada uno."

## Scope

Este spec cubre dos mejoras de usabilidad sobre la cuadrícula anual de cumplimiento del proveedor (spec 006):

1. **Refresco automático del grid** tras la carga de un nuevo documento con vigencia, para que el estado de cada celda refleje inmediatamente el cambio sin que el usuario tenga que recargar la página.
2. **Leyenda de colores** visible junto al grid, que explica qué significa cada estado de celda (color + etiqueta), eliminando la necesidad de memorizar el código visual.

Depende de: [spec 006 - supplier-compliance-view](../006-supplier-compliance-view/spec.md) (cuadrícula anual) y [spec 001 - repse-compliance-tracker](../001-repse-compliance-tracker/spec.md) (carga de documentos).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refresco inmediato del grid al subir un documento (Priority: P1)

Un gestor abre el detalle de un proveedor, sube un documento de cumplimiento mensual para el periodo actual y, sin ninguna acción adicional, la cuadrícula anual actualiza el estado de la celda correspondiente al mes recién cubierto — pasando, por ejemplo, de "Faltante" a "Vigente".

**Why this priority**: La razón de tener el grid en tiempo real es que el usuario vea el impacto de su acción de forma inmediata. Sin este refresco, el usuario no sabe si el documento se procesó correctamente y puede confundirse pensando que el estado no cambió.

**Independent Test**: Un gestor sube un documento para un tipo y periodo que actualmente aparece como "Faltante" en el grid. Sin recargar la página, la celda cambia a "Vigente" (o "Enviado", según el estado calculado). Se puede probar con un solo documento en un solo periodo.

**Acceptance Scenarios**:

1. **Given** un proveedor con al menos una celda en estado "Faltante" en el grid anual, **When** el gestor sube un documento para ese tipo de documento y el periodo correspondiente, **Then** la celda del grid para ese mes se actualiza automáticamente al nuevo estado calculado (p. ej. "Vigente") sin que el usuario recargue la página.
2. **Given** el diálogo de carga de documentos abierto desde el detalle del proveedor, **When** la carga se completa exitosamente, **Then** el diálogo se cierra y el grid refleja el nuevo estado en menos de 2 segundos.
3. **Given** un documento subido que produce estado "Por vencer" (dentro del umbral configurado), **When** el grid se refresca, **Then** la celda muestra el estado "Por vencer" con su color correspondiente.
4. **Given** que la carga falla (error de red, archivo inválido, etc.), **When** el diálogo muestra el error, **Then** el grid NO se refresca (no hay cambio de estado) y mantiene el estado anterior.

---

### User Story 2 - Leyenda de colores visible en el grid de cumplimiento (Priority: P1)

Cualquier usuario que visualiza la cuadrícula anual de cumplimiento de un proveedor puede consultar, en la misma pantalla, un recuadro o lista que explica qué significa cada color de celda, sin necesidad de buscar documentación externa.

**Why this priority**: El grid usa hasta siete estados visuales distintos. Un usuario nuevo o poco frecuente no puede recordar todos los colores sin referencia. La leyenda elimina la fricción de "¿qué significa el gris claro?" y reduce errores de interpretación que podrían llevar a acciones incorrectas (p. ej. marcar un proveedor como incumplido cuando en realidad está en un periodo futuro).

**Independent Test**: Un usuario abre el detalle de cualquier proveedor con el grid visible y puede leer, en la misma pantalla, todos los colores posibles con sus etiquetas descriptivas sin necesidad de ninguna interacción adicional.

**Acceptance Scenarios**:

1. **Given** cualquier usuario con acceso al detalle de un proveedor, **When** el grid anual de cumplimiento está visible, **Then** la leyenda de colores está visible en la misma pantalla sin necesidad de desplazamiento adicional o clic extra.
2. **Given** la leyenda de colores visible, **When** el usuario la lee, **Then** muestra al menos los siguientes siete estados con su color e icono/etiqueta: Validado, Enviado, Vencido, Faltante, Pendiente, Futuro, No requerido.
3. **Given** la leyenda de colores visible, **When** el estado de una celda en el grid coincide con un ítem de la leyenda, **Then** el color de la muestra en la leyenda es visualmente idéntico al color de la celda en el grid.
4. **Given** una pantalla de escritorio estándar (≥ 1280 px de ancho), **When** el grid y la leyenda están visibles juntos, **Then** ambos elementos se presentan sin superponerse y sin requerir scroll horizontal.

---

### Edge Cases

- ¿Qué pasa si el proveedor no tiene documentos de ningún tipo? La leyenda se muestra igualmente, ya que es estática y sirve de referencia para los estados que podrían aparecer en el futuro.
- ¿Qué pasa si el refresco del grid tarda más de lo esperado (latencia alta)? Se muestra un indicador de carga sobre el grid mientras se obtienen los datos actualizados; el estado anterior permanece visible como placeholder.
- ¿Qué pasa si el documento se sube desde una pantalla diferente al detalle del proveedor (p. ej. desde la página global `/documents`)? El refresco aplica únicamente al grid del proveedor que se está visualizando en ese momento; los grids de otros proveedores no necesitan refrescarse.
- ¿Qué pasa si el año seleccionado en el grid es diferente al año del periodo del documento recién subido? El refresco actualiza el grid para el año actualmente visible; si el documento corresponde a otro año, el cambio se verá al navegar a ese año.
- ¿Qué pasa en pantallas pequeñas (< 768 px)? La leyenda puede colapsar en un elemento expandible (acordeón o botón "Ver leyenda") para no consumir espacio en pantallas pequeñas; en escritorio siempre está desplegada.

## Requirements *(mandatory)*

### Functional Requirements

**Refresco del grid**

- **FR-001**: Tras la carga exitosa de un documento desde el detalle de un proveedor, el sistema DEBE invalidar y volver a obtener los datos de la cuadrícula anual de cumplimiento de ese proveedor automáticamente, sin intervención del usuario.
- **FR-002**: El refresco DEBE reflejar el nuevo estado de cumplimiento calculado por el backend (vigente, por vencer, vencido, enviado, validado) en la celda correspondiente al tipo de documento y periodo recién cubierto.
- **FR-003**: Durante el refresco, el sistema DEBE mostrar un indicador visual de carga que no oculte ni destruya el grid existente; el layout del grid no debe cambiar durante la actualización.
- **FR-004**: Si la carga del documento falla, el sistema NO DEBE disparar el refresco del grid; el estado visible del grid debe ser el mismo que antes de intentar la carga.
- **FR-005**: El refresco DEBE completarse y mostrar el nuevo estado al usuario en condiciones normales de red en menos de 3 segundos desde que el diálogo de carga confirma el éxito.

**Leyenda de colores**

- **FR-006**: La pantalla de detalle del proveedor DEBE mostrar una leyenda de colores que describa cada uno de los siete estados posibles de la cuadrícula anual: Validado, Enviado, Vencido, Faltante, Pendiente, Futuro, No requerido.
- **FR-007**: Cada ítem de la leyenda DEBE incluir: (1) una muestra del color exacto usado en el grid, y (2) la etiqueta descriptiva en español.
- **FR-008**: La leyenda DEBE ser estática y siempre visible en pantallas de escritorio (≥ 1280 px) sin requerir interacción del usuario para mostrarse.
- **FR-009**: En pantallas menores a 768 px, la leyenda PUEDE presentarse de forma compacta (colapsada por defecto con opción de expandir) para preservar el espacio de pantalla.
- **FR-010**: Los colores e íconos de la leyenda DEBEN ser visualmente consistentes con los colores e íconos del grid; no debe haber discrepancia cromática perceptible entre leyenda y celdas reales.

### Key Entities

- **Cuadrícula anual de cumplimiento (ComplianceGrid)**: Componente existente (spec 006) que muestra el estado de cada tipo de documento por mes. Recibe datos del endpoint `GET /api/v1/suppliers/{id}/compliance?year=YYYY`.
- **Estado de celda (CellStatus)**: Enumeración de siete valores: `validated`, `submitted`, `expired`, `missing`, `pending`, `future`, `not_required`. Cada valor tiene un color e icono asociado en el diseño.
- **Leyenda de colores (ComplianceLegend)**: Nuevo componente visual que mapea cada `CellStatus` a su color e etiqueta descriptiva en español.
- **Diálogo de carga (UploadDialog)**: Componente existente (spec 001) que al cerrarse con éxito debe disparar la invalidación del caché del grid del proveedor actual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras la carga exitosa de un documento, el grid del proveedor muestra el nuevo estado correcto en menos de 3 segundos sin que el usuario recargue la página, medido en condiciones de red estándar.
- **SC-002**: El 100% de los estados de celda del grid tiene un ítem correspondiente en la leyenda, verificado mediante inspección visual de la leyenda contra los siete valores posibles de `CellStatus`.
- **SC-003**: Un usuario nuevo que ve el grid por primera vez puede identificar correctamente el significado de al menos 6 de los 7 estados de celda consultando únicamente la leyenda, sin documentación adicional, medido en prueba de usabilidad con al menos 3 participantes.
- **SC-004**: La leyenda es visible sin desplazamiento adicional en al menos el 90% de las resoluciones de escritorio comunes (≥ 1280 px de ancho), verificado en los tres navegadores principales (Chrome, Firefox, Edge).

## Assumptions

- El grid ya está implementado (spec 006) y los datos se obtienen vía `GET /api/v1/suppliers/{id}/compliance?year=YYYY`; este spec no requiere cambios en el backend ni en el modelo de datos.
- El diálogo de carga de documentos (`UploadDialog`) ya existe (spec 001); solo se modifica para que, al cerrarse con éxito, dispare la invalidación del caché de React Query para la cuadrícula del proveedor.
- Los siete estados de celda y sus colores ya están definidos e implementados en el componente `ComplianceCell`; la leyenda reutiliza los mismos tokens de color, no define nuevos.
- El refresco automático se implementa mediante invalidación de caché en el cliente (React Query), aprovechando el mismo endpoint ya existente; no requiere WebSockets ni push del servidor.
- El año seleccionado en el grid es manejado por el componente padre; el refresco aplica al año actualmente visible, no a todos los años.
- La leyenda se implementa como un componente estático nuevo (`ComplianceLegend`) ubicado cerca del grid en el detalle del proveedor; no requiere nuevos endpoints de API.
