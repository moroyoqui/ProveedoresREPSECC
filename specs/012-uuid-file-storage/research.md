# Research: UUID Suffix en Nombres de Archivo de Documentos

**Feature**: 012-uuid-file-storage | **Date**: 2026-06-08

---

## Decisión 1: Biblioteca y versión de UUID

**Decision**: `uuid.uuid4()` de la biblioteca estándar de Python (`import uuid`)

**Rationale**: UUID4 (aleatorio) no depende de MAC address ni timestamp predecibles, es seguro para nombres de archivo públicamente referenciados, y no requiere dependencias externas. La biblioteca estándar garantiza disponibilidad en todos los entornos del proyecto.

**Alternatives considered**:
- `uuid.uuid1()` (timestamp + MAC): descartado por filtración de información de hardware.
- `secrets.token_hex(16)`: equivalente en entropía pero menos estándar; el formato UUID es más reconocible en logs y debugging.
- `shortuuid` (biblioteca externa): descartado por YAGNI; no agrega valor sobre stdlib.

---

## Decisión 2: Formato del nombre de archivo

**Decision**: `v{version}.{uuid4_canonical}.{ext}`

Ejemplo: `v1.550e8400-e29b-41d4-a716-446655440000.pdf`

Ruta completa: `{organization_id}/{supplier_id}/{document_id}/v{version}.{uuid4}.{ext}`

**Rationale**:
- La representación canónica de UUID4 (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`, 36 caracteres) es compatible con ext4, xfs, NTFS, HFS+ y todos los sistemas de archivos relevantes.
- Mantener el prefijo `v{version}` preserva la legibilidad y la trazabilidad humana en el sistema de archivos.
- Añadir el UUID entre la versión y la extensión (`.` como separador en ambos lados) evita ambigüedad en el parsing de extensiones.
- La longitud máxima de la ruta resultante: `19 (ids) + 3 (separadores /) + 8 (v{ver}.) + 36 (uuid) + 1 (.) + 4 (ext) ≈ 71 chars`. Muy por debajo del límite de `String(1024)` de la columna `file_path`.

**Alternatives considered**:
- Sufijo al final (`v1.pdf.{uuid}`): descartado por romper la detección de extensiones estándar de los sistemas operativos.
- UUID como directorio adicional (`{uuid}/v1.pdf`): descartado por complejidad innecesaria y sin ventaja sobre incluirlo en el nombre.
- Prefijo en lugar de sufijo (`{uuid}.v1.pdf`): descartado por oscurecer la numeración de versión a simple vista.

---

## Decisión 3: Migración de archivos existentes

**Decision**: No se requiere migración.

**Rationale**: Los archivos ya almacenados tienen rutas válidas en la columna `file_path` del registro `Document`. El código de descarga (`FileStore.open()`) y el de eliminación (`FileStore.delete()`) operan sobre la ruta almacenada, no sobre una ruta reconstruida. La validación de path traversal valida cualquier ruta sin importar su formato. Los archivos nuevos usarán UUID; los existentes seguirán funcionando con sus rutas antiguas indefinidamente.

**Alternatives considered**:
- Migración retroactiva de todos los archivos: descartado por riesgo operativo alto (mover archivos en producción) sin beneficio funcional.
- Script de migración opcional: innecesario dado que no hay colisión de rutas antiguas con las nuevas.

---

## Decisión 4: Punto de inserción del UUID en el código

**Decision**: Modificar únicamente `FileStore.save()` en `backend/src/repse/documents/storage.py` (línea 58).

**Rationale**: `FileStore.save()` es el único lugar donde se construye `rel` (la ruta relativa). Todo el código que escribe, lee o elimina archivos recibe la ruta ya construida desde `stored.relative_path` o desde `doc.file_path`. La modificación está completamente encapsulada.

**Affected callers** (solo leen la ruta, no la construyen):
- `documents/service.py:184` — `doc.file_path = stored.relative_path`
- `documents/routes.py:174` — `store.open(doc.file_path)`
- `suppliers/type_change_service.py:221` — `store.delete(doc.file_path)`
- Portal `routes.py:191` — llama a `upload_document` que delega en `service.py`

Ningún caller necesita cambios.

---

## Decisión 5: Tests a añadir

**Decision**: Añadir test unitario en `backend/tests/unit/test_file_storage.py` que verifique:
1. Que dos llamadas a `FileStore.save()` con los mismos parámetros producen rutas distintas.
2. Que la ruta generada contiene un UUID4 válido en el formato correcto.

**Rationale**: El cambio es de una línea pero tiene implicaciones en la unicidad de rutas. Un test explícito documenta el contrato y previene regresiones.

---

## Compatibilidad con restricción de deduplicación SHA-256

La restricción `UniqueConstraint("organization_id", "file_sha256")` sigue funcionando igual. Si el mismo archivo (mismo SHA-256, misma organización) se intenta subir dos veces, el sistema lanza `Conflict` **antes** de llamar a `FileStore.save()`. Por lo tanto, el UUID solo entra en juego para contenido efectivamente distinto o para documentos de organizaciones diferentes que casualmente tienen el mismo contenido (lo cual está permitido por la restricción que incluye `organization_id`).
