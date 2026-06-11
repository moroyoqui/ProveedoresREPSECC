# Feature Specification: UUID Suffix en Nombres de Archivo de Documentos

**Feature Branch**: `012-uuid-file-storage`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "Quiero que modifiques la definición de la manera en que se están almacenando los archivos de los documentos de los proveedores en los directorios, para que contemples que se pueden duplicar los nombres de los archivos. Entonces, lo que sugiero es que se agregue un subfijo tipo UUID al final del nombre del documento, seguido del punto, y luego la extensión."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Subida de documento genera ruta única garantizada (Priority: P1)

Cuando un operador sube un documento de proveedor, el sistema almacena el archivo con un sufijo UUID4 en el nombre, garantizando que nunca habrá colisión de rutas en disco, incluso si el mismo tipo de archivo se sube repetidamente o en forma concurrente.

**Why this priority**: La unicidad de rutas es un requisito de integridad de datos. Sin ella, una subida posterior podría sobrescribir silenciosamente un archivo previo.

**Independent Test**: Se puede verificar subiendo el mismo tipo de documento dos veces para el mismo proveedor y confirmando que ambos archivos existen en disco con rutas distintas.

**Acceptance Scenarios**:

1. **Given** un proveedor existente, **When** se suben dos documentos del mismo tipo, **Then** cada archivo se almacena en una ruta diferente con un UUID único en el nombre.
2. **Given** una subida de documento, **When** el archivo se persiste en disco, **Then** la ruta almacenada en la base de datos incluye el UUID4 y coincide exactamente con la ruta física del archivo.
3. **Given** dos subidas concurrentes del mismo documento, **When** ambas se completan, **Then** ambos archivos existen en disco sin que ninguno haya sobreescrito al otro.

---

### User Story 2 - Descarga transparente para el usuario (Priority: P2)

Cuando un usuario autorizado descarga un documento, recibe el archivo correcto. La presencia del UUID en la ruta interna del archivo es completamente transparente: el nombre que ve el usuario al descargar no incluye el UUID.

**Why this priority**: El comportamiento de descarga no debe degradarse por el cambio interno de nomenclatura.

**Independent Test**: Se puede probar subiendo un archivo y luego descargándolo, verificando que el contenido es idéntico al original.

**Acceptance Scenarios**:

1. **Given** un documento almacenado con UUID en la ruta, **When** se solicita su descarga, **Then** el sistema sirve el archivo correcto con el tipo MIME adecuado.
2. **Given** un documento con UUID en la ruta, **When** se verifica su integridad, **Then** el hash SHA-256 almacenado coincide con el del archivo físico en disco.

---

### User Story 3 - Compatibilidad con documentos existentes (Priority: P3)

Los documentos subidos antes de la implementación de este cambio (cuyas rutas no contienen UUID) siguen siendo accesibles sin ninguna migración manual.

**Why this priority**: La retrocompatibilidad protege datos ya almacenados. La migración de archivos existentes es costosa y riesgosa.

**Independent Test**: Se puede verificar que las rutas antiguas (formato `v{version}.{ext}`) siguen respondiendo correctamente a solicitudes de descarga.

**Acceptance Scenarios**:

1. **Given** un documento cuya ruta fue generada con el formato anterior (sin UUID), **When** se solicita su descarga, **Then** el sistema lo sirve correctamente.
2. **Given** una instalación existente con documentos ya almacenados, **When** se despliega el nuevo código, **Then** no se requiere ejecutar ningún script de migración de archivos.

---

### Edge Cases

- ¿Qué sucede si la generación del UUID falla en tiempo de ejecución? El sistema debe rechazar la subida con error claro, no guardar el archivo con ruta inválida.
- ¿Qué ocurre si se intenta eliminar un archivo cuya ruta incluye UUID pero el UUID es incorrecto (path traversal)? La validación de path traversal existente debe seguir protegiéndolo.
- ¿Cómo se comporta el sistema si el UUID generado contiene caracteres incompatibles con el sistema de archivos del servidor? UUID4 en su representación canónica (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`) es seguro en todos los sistemas de archivos relevantes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Al guardar un archivo de documento, el sistema DEBE generar un UUID4 y añadirlo como sufijo al nombre del archivo, entre el prefijo de versión y la extensión (formato: `v{version}.{uuid}.{ext}`).
- **FR-002**: El UUID DEBE ser generado de forma aleatoria (UUID4) en cada subida, sin reutilizar valores previos.
- **FR-003**: La ruta relativa completa del archivo (incluyendo el UUID) DEBE almacenarse en el registro del documento en la base de datos, de modo que sea la única fuente de verdad para localizar el archivo.
- **FR-004**: Las operaciones de lectura (`open`) y eliminación (`delete`) de archivos DEBEN usar la ruta almacenada en el registro, sin reconstruirla a partir de otros campos.
- **FR-005**: Los documentos existentes cuyas rutas no contienen UUID DEBEN seguir siendo accesibles y descargables sin modificación.
- **FR-006**: La protección contra path traversal DEBE mantenerse intacta independientemente del formato del nombre de archivo.

### Key Entities

- **Document (registro de documento)**: Entidad existente. El campo `file_path` (ruta relativa) pasa a almacenar la nueva nomenclatura con UUID. No se añaden campos nuevos.
- **StoredFile (resultado de guardado)**: Estructura de datos que describe el archivo guardado en disco; su campo `relative_path` refleja el nuevo formato con UUID.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cero colisiones de rutas en disco: dos subidas del mismo documento para el mismo proveedor producen siempre dos archivos físicamente distintos.
- **SC-002**: El 100% de los documentos descargados tras el cambio son íntegros: el hash SHA-256 del archivo físico coincide con el almacenado en la base de datos.
- **SC-003**: El 100% de los documentos subidos antes del cambio siguen siendo descargables sin intervención manual.
- **SC-004**: El tiempo de subida de documentos no aumenta en más de 10 ms respecto al comportamiento previo (la generación de UUID es despreciable).

## Assumptions

- Se asume que `uuid.uuid4()` de la biblioteca estándar de Python es suficiente para la generación de UUIDs; no se requiere una librería externa.
- Se asume que no es necesario migrar archivos existentes a la nueva nomenclatura; los documentos ya almacenados seguirán siendo accesibles con su ruta original.
- Se asume que el cambio solo afecta al módulo de almacenamiento en disco (`FileStore`); la base de datos, el OCR, y el sistema de tokens de descarga no requieren modificaciones estructurales.
- Se asume que la representación canónica de UUID4 (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`, 36 caracteres) es compatible con el sistema de archivos de destino (Linux ext4/xfs en Docker).
- Se asume que la extensión del archivo se sigue derivando del tipo MIME del archivo subido, igual que antes.
