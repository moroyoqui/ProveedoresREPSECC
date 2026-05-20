# Tasks: Carga Múltiple y Visualizador de Documentos

**Input**: Design documents from `specs/008-multi-upload-doc-viewer/`

**Note**: No hay plan.md aún; las tareas se derivan del `spec.md` de esta feature y del código existente auditado (spec 006 + 007 implementados). Stack heredado: React 18 + Vite + Tailwind + TanStack Query (frontend), FastAPI + SQLAlchemy 2 + MySQL 8 (backend).

**Tests**: No se generan test tasks a menos que se soliciten explícitamente.

**References**:
- `frontend/src/components/documents/UploadDialog.tsx` — diálogo de carga (actual: un archivo)
- `frontend/src/components/documents/DocumentViewerModal.tsx` — visor de documentos
- `frontend/src/components/suppliers/ComplianceCell.tsx` — esfera de cumplimiento
- `frontend/src/components/suppliers/ComplianceGrid.tsx` — cuadrícula anual
- `frontend/src/lib/api/documents.ts` — hooks y tipos de la API de documentos
- `backend/src/repse/documents/routes.py` — endpoints de documentos
- `backend/src/repse/compliance/schemas.py` — CellOut (sin document_count)
- `backend/src/repse/compliance/service.py` — servicio del grid anual

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo con otras tareas [P] del mismo bloque
- **[Story]**: Historia de usuario a la que pertenece la tarea

---

## Phase 1: Setup (Infraestructura compartida)

**Purpose**: No se requiere setup nuevo; esta feature extiende infraestructura ya instalada.

No hay tareas en esta fase. Continúa en Phase 2.

---

## Phase 2: Foundational (Prerrequisitos bloqueantes)

**Purpose**: Cambios de backend y tipos frontend que desbloquean la implementación de todas las historias de usuario. DEBEN completarse antes de iniciar cualquier story.

**⚠️ CRÍTICO**: No empieces US1/US2/US3 hasta completar esta fase.

- [x] T001 Agregar parámetro `coverage_period_start: date | None` al endpoint `GET /api/v1/documents` en `backend/src/repse/documents/routes.py`, aplicando el filtro `Document.coverage_period_start == coverage_period_start` solo cuando no es `None`
- [x] T002 [P] Agregar campos `coverage_period_start?: string` y `is_latest?: boolean` a `DocumentListFilters`, y actualizar `buildDocumentsUrl` para incluirlos en la query string en `frontend/src/lib/api/documents.ts`

**Checkpoint**: El endpoint `GET /api/v1/documents?supplier_id=X&document_type_id=Y&coverage_period_start=Z&is_latest=false` devuelve todos los documentos (incluyendo versiones anteriores) de esa celda.

---

## Phase 3: User Story 1 - Subir múltiples archivos (Priority: P1) 🎯 MVP

**Goal**: El usuario puede seleccionar N archivos en el diálogo de carga, subirlos en una sola operación y ver el estado individual de cada archivo (en espera, subiendo, éxito, error).

**Independent Test**: Abrir el diálogo de carga, seleccionar 3+ archivos, confirmar, verificar que cada uno aparece en la BD con el mismo proveedor/tipo/período.

### Implementación US1

- [x] T003 [US1] Reemplazar `useState<File | null>(null)` por `useState<FileItem[]>([])` donde `FileItem = { file: File; status: "idle" | "uploading" | "success" | "error"; error?: string }` en `frontend/src/components/documents/UploadDialog.tsx`

- [x] T004 [US1] Actualizar el `<input type="file">` en `frontend/src/components/documents/UploadDialog.tsx` para:
  - Agregar atributo `multiple`
  - Cambiar `onChange` para leer `e.target.files` completo y construir el array `FileItem[]`
  - Reemplazar el mensaje de estado único por una lista `<ul>` que muestra nombre y estado (ícono/spinner/✓/✗) de cada archivo seleccionado

- [x] T005 [US1] Reemplazar la lógica de `handleSubmit` en `frontend/src/components/documents/UploadDialog.tsx` para:
  - Iterar sobre el array de archivos en orden
  - Llamar `upload.mutateAsync(...)` por cada archivo (secuencial para evitar condiciones de carrera en el campo `is_latest`)
  - Actualizar el estado individual de cada `FileItem` a `"uploading"`, luego `"success"` o `"error"` según el resultado
  - Continuar con el siguiente archivo aunque el anterior falle

- [x] T006 [US1] Actualizar el cierre del diálogo en `frontend/src/components/documents/UploadDialog.tsx`:
  - Mostrar un resumen final: "N de M archivos subidos correctamente" cuando haya fallos
  - Deshabilitar el botón "Subir" mientras algún archivo esté en estado `"uploading"`
  - Llamar `onClose(true)` solo cuando al menos un archivo se subió con éxito (para refrescar el grid)
  - Si todos fallaron, mostrar el resumen de errores y NO cerrar el diálogo automáticamente; ofrecer un botón "Reintentar fallidos" que resetea a `"idle"` solo los archivos con error

**Checkpoint**: El diálogo acepta múltiples archivos, muestra progreso individual y maneja éxitos/fallos parciales sin cerrar innecesariamente.

---

## Phase 4: User Story 2 - Visualizar documentos desde la esfera (Priority: P1)

**Goal**: Al hacer clic en una esfera verde/amarilla/vencida, se abre un modal con la lista de todos los documentos de esa celda, permitiendo previsualizar y descargar cada uno.

**Independent Test**: Hacer clic en una esfera verde de un proveedor con documentos cargados; verificar que el modal muestra la lista, la vista previa funciona y el botón de descarga inicia la descarga.

### Implementación US2

- [x] T007 [P] [US2] Crear `frontend/src/components/documents/DocumentViewerModal.tsx` con las siguientes responsabilidades:
  - Props: `{ supplierId: number; documentTypeId: number; coveragePeriodStart: string | null; onClose: () => void }`
  - Usar `useDocumentsList({ supplier_id: supplierId, document_type_id: documentTypeId, coverage_period_start: coveragePeriodStart ?? undefined, is_latest: false })` para cargar todos los documentos de la celda
  - Renderizar el modal como overlay fijo (`fixed inset-0 z-50`) con panel lateral derecho (`w-[640px]`) o modal centrado (`max-w-3xl`), eligiendo panel lateral para mantener visible el contexto de la cuadrícula
  - Panel izquierdo: lista de archivos con nombre, tamaño formateado (KB/MB), fecha de carga, badge de estado (`verified` / `pending`), botón de descarga por archivo
  - Panel derecho: área de preview; para PDF usa `<iframe src={previewUrl}>`, para imágenes usa `<img src={previewUrl}>`, para otros formatos muestra ícono de tipo de archivo + mensaje "Vista previa no disponible" + botón de descarga prominente
  - Navegación entre archivos: botones "← Anterior" / "Siguiente →" y resalte del ítem activo en la lista
  - Cerrar: botón ✕, clic en backdrop, tecla Escape (usando `useEffect` con `keydown` listener)
  - Estado de carga: esqueleto mientras `isLoading`; mensaje "No hay documentos" si la lista está vacía

- [x] T008 [US2] Agregar un hook `useDownloadToken` en `frontend/src/lib/api/documents.ts` que llame a `POST /api/v1/documents/{documentId}/download-token` y retorne la URL construida para `GET /api/v1/files/{token}`. Este hook es usado por `DocumentViewerModal` para obtener URLs temporales de preview y descarga.

- [x] T009 [US2] Actualizar el tipo `ViewerClickParams = { document_type_id: number; coverage_period_start: string | null }` en `frontend/src/components/suppliers/ComplianceCell.tsx`:
  - Reemplazar `onDocumentClick?: (documentId: number) => void` por `onViewerClick?: (params: ViewerClickParams) => void`
  - Actualizar la condición `canOpenDoc` para usar `onViewerClick` en lugar de `onDocumentClick`
  - En el handler del botón de la esfera, llamar `onViewerClick({ document_type_id: document_type_id!, coverage_period_start: coverage_period_start ?? null })`
  - Exportar el tipo `ViewerClickParams` para uso en `ComplianceGrid`

- [x] T010 [US2] Actualizar `frontend/src/components/suppliers/ComplianceGrid.tsx`:
  - Cambiar la prop `onDocumentClick?: (documentId: number) => void` por `onViewerClick?: (params: ViewerClickParams) => void`
  - Agregar estado local `const [viewerCell, setViewerCell] = useState<ViewerClickParams & { documentTypeId: number } | null>(null)`
  - En cada `<ComplianceCell>`, pasar `onViewerClick={(params) => setViewerCell({ ...params, documentTypeId: req.document_type.id })}` para celdas con documento
  - Renderizar `<DocumentViewerModal>` cuando `viewerCell !== null`, con `onClose={() => setViewerCell(null)}`

- [x] T011 [US2] Actualizar la página `frontend/src/pages/suppliers/detail.tsx` para:
  - Eliminar el handler `onDocumentClick` que antes abría la vista de documento individual
  - Verificar que el grid ahora abre el `DocumentViewerModal` sin intervención de la página padre
  - Ajustar si existía lógica en `detail.tsx` que dependía del `documentId` recibido

**Checkpoint**: El clic en una esfera con documentos abre el modal/panel lateral, lista los archivos del período, permite previsualizar PDF e imágenes y descargar cualquier archivo. Escape cierra el modal.

---

## Phase 5: User Story 3 - Indicador de conteo en la esfera (Priority: P2)

**Goal**: Cuando una celda tiene más de un documento, la esfera muestra un pequeño badge numérico para que el usuario sepa de un vistazo cuántos archivos están registrados.

**Independent Test**: Subir 2 archivos para un período, recargar la cuadrícula, verificar que la esfera correspondiente muestra el badge "2".

### Implementación US3 (conteo)

- [x] T012 [P] [US3] Agregar campo `document_count: int = 0` a la clase `CellOut` en `backend/src/repse/compliance/schemas.py`

- [x] T013 [US3] Actualizar `backend/src/repse/compliance/service.py` para computar `document_count` al construir cada celda:
  - Para cada celda que tenga `status != NOT_REQUIRED`, ejecutar `SELECT COUNT(*) FROM documents WHERE supplier_id=? AND document_type_id=? AND coverage_period_start=? AND deleted_at IS NULL`
  - Asignar el conteo al campo `document_count` de `CellOut`
  - Para celdas con status `MISSING`, `FUTURE` o `NOT_REQUIRED`, dejar `document_count = 0`

- [x] T014 [US3] Actualizar `frontend/src/components/suppliers/ComplianceCell.tsx`:
  - Agregar prop `document_count?: number` a `ComplianceCellProps`
  - Cuando `document_count` es 2 o más, renderizar un badge posicionado en superíndice sobre la esfera: `<span class="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-brand-600 text-[9px] text-white flex items-center justify-center">{document_count}</span>` dentro de un `<span class="relative">` que envuelve la esfera
  - Actualizar el tooltip para incluir el conteo: p.ej. `"Enero: Validado (2 archivos)"`

- [x] T015 [US3] Verificar que `ComplianceGrid.tsx` pasa el campo `document_count` de cada `CellOut` al prop correspondiente de `ComplianceCell` (el campo ya estará disponible una vez que el backend lo incluya en la respuesta del endpoint de compliance)

**Checkpoint**: Las esferas con más de un documento muestran el badge de conteo. Las esferas con un solo documento o sin documento no muestran badge.

---

## Phase 6: US2 Update — Vista previa sin descarga automática (Priority: P1)

**Goal**: El visor muestra el contenido de PDFs e imágenes directamente en el panel sin disparar ninguna descarga automática. El endpoint de archivos ahora soporta modo inline (`?inline=1`) para que el navegador renderice el contenido en lugar de descargarlo. La descarga explícita sigue funcionando con el botón "Descargar".

**Contexto técnico**: El endpoint `GET /api/v1/files/{token}` (línea 174 de `routes.py`) actualmente siempre responde con `Content-Disposition: attachment`, lo que hace que el `<iframe>` del modal abra un diálogo de descarga en lugar de mostrar el PDF. El `<img>` también puede verse afectado en algunos navegadores.

**Independent Test**: Hacer clic en una esfera verde con un PDF; verificar que el visor muestra el contenido del PDF embebido en el panel sin abrir ningún diálogo de descarga del navegador. Luego hacer clic en "Descargar" y verificar que el archivo se descarga normalmente.

### Implementación US2 Update

- [ ] T019 [US2] Actualizar `backend/src/repse/documents/routes.py` en el endpoint `GET /api/v1/files/{token}` (líneas 150-176):
  - Agregar query param `inline: bool = False` a la firma
  - Cuando `inline is True`, responder con `Content-Disposition: inline; filename="{doc.file_name_original}"` en lugar de `attachment; filename="..."`
  - El resto de la lógica (autenticación JWT, verificación del token, comprobación de tenant, lectura del archivo con `store.open`) permanece exactamente igual

- [ ] T020 [US2] Actualizar `frontend/src/components/documents/DocumentViewerModal.tsx`:
  - En el `useEffect` que obtiene el token y construye la URL de preview (líneas 58-82), cambiar la URL fuente del `<iframe>` y del `<img>` de `/api/v1/files/${previewToken}` a `/api/v1/files/${previewToken}?inline=1` (líneas 263 y 269)
  - En `handleDownload` (líneas 102-112), mantener la URL sin el parámetro `?inline=1` para que el navegador fuerce la descarga como archivo adjunto
  - No se requiere ningún otro cambio; el token es el mismo para ambos modos

**Checkpoint**: El visor renderiza PDFs e imágenes directamente en el panel sin diálogos de descarga. El botón "Descargar" sigue siendo el único camino para obtener el archivo en disco.

---

## Phase 7: New US3 — Carga adicional desde el visualizador (Priority: P1)

**Goal**: Cuando el visualizador muestra documentos de una celda no verificada, aparece una opción "Agregar documento" en el panel lateral. El usuario puede seleccionar y subir archivos adicionales sin cerrar el modal; la lista se refresca automáticamente tras cada carga exitosa. En celdas verificadas, la opción no aparece.

**Contexto técnico**: El `DocumentViewerModal` ya carga la lista de documentos con `useDocumentsList`. El endpoint de upload `POST /api/v1/suppliers/{supplierId}/documents` ya existe y acepta los parámetros necesarios. Solo hay que agregar la UI de carga adicional y la lógica de llamada al endpoint, condicional al estado de verificación de la celda.

**Independent Test**: Abrir el visualizador de una celda verde no verificada; verificar que aparece el botón "Agregar documento" en el panel lateral; subir un archivo adicional y verificar que aparece en la lista sin cerrar el modal. Repetir con una celda verificada y confirmar que el botón NO aparece.

### Implementación New US3

- [ ] T021 [P] [US3] Agregar prop `canAddDocuments?: boolean` al tipo `DocumentViewerParams` en `frontend/src/components/documents/DocumentViewerModal.tsx` (líneas 26-31) y recibirla en la firma del componente (línea 35) con valor por defecto `false`

- [ ] T022 [P] [US3] Actualizar `frontend/src/components/suppliers/ComplianceGrid.tsx` en la sección que construye el estado `viewerCell` y renderiza `<DocumentViewerModal>`:
  - El tipo de `viewerCell` debe incluir el campo `cellVerified: boolean` (o `cellStatus: string`) tomado del `CellOut` de la celda seleccionada
  - Al renderizar `<DocumentViewerModal>`, pasar `canAddDocuments={!viewerCell.cellVerified}` (o equivalente basado en el status: `viewerCell.cellStatus !== "verified"`)

- [ ] T023 [US3] Agregar sección "Agregar documento" al final del `<aside>` (panel lateral izquierdo, líneas 169-215) de `frontend/src/components/documents/DocumentViewerModal.tsx`, visible solo cuando `canAddDocuments === true`:
  - `const addFileRef = useRef<HTMLInputElement>(null)`
  - `const [addItems, setAddItems] = useState<AddFileItem[]>([])` donde `AddFileItem = { file: File; status: "idle" | "uploading" | "success" | "error"; error?: string }`
  - Un `<input type="file" multiple ref={addFileRef} className="hidden" onChange={handleAddFilesSelected} />`
  - Un `<button>` visible "Agregar documento" que llama `addFileRef.current?.click()` con estilo secundario coherente con el resto del modal
  - Un `<ul>` que muestra cada `addItem` con su estado (spinner, ✓, ✗ + mensaje) debajo del botón
  - Separador visual (`<hr>` o `border-t`) entre la lista de archivos existentes y la sección de carga adicional

- [ ] T024 [US3] Implementar `handleAddFilesSelected` y `handleAddUpload` en `frontend/src/components/documents/DocumentViewerModal.tsx`:
  - `handleAddFilesSelected(e)`: leer `e.target.files`, construir el array `AddFileItem[]` con todos en `"idle"` y actualizar `addItems`; limpiar el input para permitir volver a seleccionar el mismo archivo
  - `handleAddUpload()`: disparado vía `useEffect` cuando `addItems` cambia y alguno está en `"idle"`; iterar secuencialmente, cambiar estado a `"uploading"`, llamar `documentsApi.upload(supplierId, documentTypeId, coveragePeriodStart, item.file)` (ver T025), actualizar a `"success"` o `"error"` según resultado; al terminar la iteración, si al menos uno tuvo éxito llamar `refetch()` y limpiar `addItems` tras 2 s para que el usuario vea el feedback

- [ ] T025 [US3] Verificar en `frontend/src/lib/api/documents.ts` si ya existe un método `documentsApi.upload(...)` que construya el `FormData` y llame `POST /api/v1/suppliers/{supplierId}/documents`:
  - Si existe (por ejemplo, usado por `UploadDialog`), reutilizarlo directamente en T024 sin duplicarlo
  - Si no existe como método en `documentsApi`, agregar `upload(supplierId: number, documentTypeId: number, coveragePeriodStart: string | null, file: File): Promise<void>` que construya el `FormData` con los campos `document_type_id`, `coverage_period_start` y `file`, y llame `POST /api/v1/suppliers/{supplierId}/documents`

**Checkpoint**: Desde el visualizador abierto para una celda no verificada se pueden agregar archivos adicionales; la lista se actualiza en vivo. En celdas verificadas el botón "Agregar documento" está oculto.

---

## Phase N: Polish & Casos límite

**Purpose**: Mejoras que aplican a múltiples historias y robustez general.

- [x] T016 [P] Agregar validación de tipo de archivo en el cliente en `frontend/src/components/documents/UploadDialog.tsx`: rechazar archivos no soportados (`ALLOWED_MIME_TYPES` del backend: PDF, PNG, JPEG, DOCX) antes de intentar la carga, marcando su `FileItem.status = "error"` con mensaje descriptivo

- [x] T017 [P] Agregar validación de tamaño máximo en el cliente en `frontend/src/components/documents/UploadDialog.tsx`: leer `file.size` y comparar contra el límite configurado (obtenerlo de una constante compartida o de la respuesta de error del backend); marcar como error inmediatamente si supera el límite

- [x] T018 Verificar que el `DocumentViewerModal` recarga la lista de archivos cuando el estado de la query es `stale` (botón "Actualizar" o `refetch` manual) en `frontend/src/components/documents/DocumentViewerModal.tsx`, para el caso en que otro usuario suba un archivo al mismo período mientras el modal está abierto

- [ ] T026 [P] Aplicar la misma validación de tipo y tamaño (T016/T017) a los archivos seleccionados en la sección "Agregar documento" del `DocumentViewerModal`: en `handleAddFilesSelected`, marcar inmediatamente como `"error"` los archivos que no cumplan tipo/tamaño antes de iniciar cualquier upload

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Phase 2 (Foundational)**: Sin dependencias — puede iniciar inmediatamente
- **Phase 3 (US1)**: Depende de Phase 2 completada (T001, T002)
- **Phase 4 (US2)**: Depende de Phase 2 completada (T001, T002); T007 puede iniciar en paralelo con T003-T006
- **Phase 5 (US3 conteo)**: Depende de Phase 4 completada (el campo `document_count` debe llegar al componente)
- **Phase 6 (US2 Update)**: Depende de Phase 4 completada (el `DocumentViewerModal` debe existir); T019 y T020 pueden ejecutarse en paralelo entre sí
- **Phase 7 (New US3)**: Depende de Phase 4 y Phase 6 completadas; T021 y T022 pueden ejecutarse en paralelo
- **Phase N (Polish)**: Depende de que las stories objetivo estén completas

### Dependencias dentro de cada historia

**US1**:
- T003 → T004 → T005 → T006 (cadena secuencial en el mismo archivo)

**US2 (original)**:
- T002 (foundational) → T007 (modal) [paralelo con T008]
- T007 + T008 → T009 → T010 → T011

**US3 (conteo)**:
- T012 (paralelo con T013) → T013 → T015 → T014

**US2 Update (no-download)**:
- T019 → T020 (backend primero; el frontend necesita que el param `?inline=1` exista)

**New US3 (carga adicional)**:
- T021 [P] + T022 [P] → T023 → T024 → T025 (verificar/agregar método)
- T026 puede hacerse en paralelo con T024

### Oportunidades de paralelismo

```
# Fase 2 - ejecutar juntos:
T001  # backend: filter coverage_period_start
T002  # frontend: actualizar DocumentListFilters

# US2 - ejecutar juntos después de T002:
T007  # DocumentViewerModal (nuevo componente)
T008  # useDownloadToken hook

# US2 Update - ejecutar juntos:
T019  # backend: inline mode en /files/{token}
T020  # frontend: usar ?inline=1 en iframe/img

# New US3 - ejecutar juntos al inicio:
T021  # agregar prop canAddDocuments al modal
T022  # pasar canAddDocuments desde ComplianceGrid
```

---

## Estrategia de implementación

### MVP completado: US1 + US2 + US3 (conteo)

1. Phase 2 (T001, T002) ✅
2. Phase 3 (US1: T003-T006) ✅
3. Phase 4 (US2: T007-T011) ✅
4. Phase 5 (US3 conteo: T012-T015) ✅

### Siguiente entrega: US2 Update + New US3

1. Phase 6 (T019, T020) → **demo: visor muestra PDFs/imágenes sin descarga automática**
2. Phase 7 (T021-T025) → **demo: agregar documentos adicionales desde el visor**
3. Phase N polish (T026) → validación en la sección de carga adicional

---

## Notas

- `[P]` = archivos distintos, sin dependencias entre sí; pueden ejecutarse simultáneamente
- `[Story]` = etiqueta de trazabilidad hacia el spec
- Las cargas múltiples se procesan **secuencialmente** (no en paralelo) para respetar la invariante `is_latest` del servicio de backend; cambiar esto a paralelo requeriría un ajuste en `upload_document` del backend
- El `DocumentViewerModal` pasa `is_latest=false` al endpoint de documentos para mostrar **todas las versiones** de la celda, no solo la más reciente
- La descarga requiere dos llamadas: primero `POST /documents/{id}/download-token`, luego `GET /files/{token}`; el token tiene TTL corto (ver `download_token_ttl_seconds` en config)
- Para US3 (conteo), el conteo en el backend suma todos los documentos no eliminados (`deleted_at IS NULL`), incluyendo versiones no-latest, para reflejar cuántos archivos existen realmente para esa celda
- **Phase 6 fix**: El param `?inline=1` es pasado por el frontend al endpoint existente; no se crea un nuevo endpoint ni un segundo tipo de token. El token es el mismo para preview y descarga
- **Phase 7**: La opción de agregar documentos es UI-only; el backend no valida si la celda está verificada al recibir el upload (comportamiento actual). Agregar validación backend queda fuera del scope de este spec
