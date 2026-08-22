# Implementation Plan: Borrado de Documentos Propios en el Back-Office

**Branch**: `016-own-document-delete` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-own-document-delete/spec.md`

## Summary

Quien carga documentos en el back-office puede hoy equivocarse de archivo, período o proveedor y no tiene forma de corregirlo: el borrado existe en el backend pero está reservado a `admin` y no tiene ningún botón en la interfaz. Esta feature amplía el permiso al **autor de la carga** y le da superficie visible.

El enfoque técnico es un delta pequeño sobre piezas existentes: `service.delete_document()` recibe `require_owner` y rechaza el borrado de documentos ajenos; la regla de estado de celda que ya usa el portal se extrae a un helper compartido; `DocumentOut` gana un campo `can_delete` calculado en el servidor; y el drawer de detalle suma un botón "Eliminar" con confirmación destructiva, siguiendo el patrón que ya usa "Quitar verificación". Sin migración de base de datos: `Document.uploaded_by` ya guarda al autor.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 / React 18 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2 (backend); Vite, Tailwind, TanStack Query v5 (frontend)

**Storage**: MySQL 8 — sin cambios de esquema en esta feature; almacenamiento de archivos en disco local vía `FileStore`

**Testing**: pytest (contract / integration / unit) desde la raíz con `backend/.venv`; Vitest y Playwright en el frontend

**Target Platform**: Docker Compose on-prem detrás de Caddy

**Project Type**: Aplicación web — backend FastAPI + SPA React

**Performance Goals**: sin impacto medible; `can_delete` no debe añadir consultas por documento en el listado (ver Constraint abajo)

**Constraints**:
- El cálculo de `can_delete` en el listado no puede degenerar en N+1 consultas sobre `PortalSubmission` y `ComplianceCellValidation`; se resuelve con una consulta agrupada por página o difiriendo el estado de celda al detalle.
- El borrado sigue siendo irreversible: no se añade papelera ni restauración.
- La convención de `portal/routes_write.py:1-14` se respeta: lógica exclusiva de un canal permanece en su ruta, no en el servicio compartido.

**Scale/Scope**: 2 archivos nuevos, ~6 archivos tocados; 1 endpoint modificado, 1 campo nuevo de respuesta, 1 botón + 1 diálogo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Veredicto |
|---|---|---|
| **I. Secure by Default** | La autorización no queda sólo en la UI: la verificación de autoría se aplica dentro de `service.delete_document()`, de modo que cualquier llamador la atraviesa. El endpoint sigue autenticado y el rol se valida antes. | ✅ PASS |
| **II. Multi-Tenant Data Isolation** | El borrado se apoya en el filtro ORM global (`db/tenant_filter.py:66`) ya activo para `Document`. Se añade test negativo explícito: un usuario de la organización A no puede borrar un documento de la B (recibe 404, no 403, para no revelar existencia). | ✅ PASS |
| **III. Test-First for Critical Paths** | Es lógica de autorización: los tests de contrato (403 sobre documento ajeno, 204 sobre propio) y el de aislamiento se escriben **antes** de tocar la ruta. Recogido en el orden de fases de abajo. | ✅ PASS |
| **IV. Simplicity and Iteration (YAGNI)** | Se reutiliza el endpoint, el servicio, la ventana de gracia, el diálogo destructivo y el helper de estado de celda existentes. No se crea endpoint nuevo, ni papelera, ni plazo de caducidad propio, ni borrado masivo. | ✅ PASS |

**Complejidad añadida que requiere justificación**: mover `_check_delete_allowed` fuera de `portal/routes_write.py` es el único cambio estructural. Se justifica porque la alternativa es duplicar una regla de negocio en dos canales que deben cambiar juntos; el movimiento es literal, sin cambio de comportamiento para el portal (ver [research.md](research.md) R3).

**Re-evaluación post-diseño (Phase 1)**: sin cambios. El diseño no introdujo entidades, servicios ni configuración nuevos; `can_delete` es un campo derivado, no persistido.

## Project Structure

### Archivos nuevos

```
backend/src/repse/compliance/cell_locks.py        # check_cell_unlocked() — movido desde portal
backend/tests/contract/test_documents_delete_contract.py
```

### Archivos modificados

```
backend/src/repse/documents/service.py            # delete_document(): parámetro require_owner + regla de autoría
backend/src/repse/documents/routes.py             # require_role(ADMIN, MANAGER); can_delete en _serialize()
backend/src/repse/portal/routes_write.py          # importa check_cell_unlocked; elimina la copia local
frontend/src/lib/api/index.ts                     # DocumentOut.can_delete; documentsApi.remove()
frontend/src/components/documents/DocumentDetailDrawer.tsx   # botón Eliminar + confirmación
frontend/src/pages/documents/list.tsx             # refresco del listado tras el borrado
```

### Sin cambios

Migraciones Alembic (no hay esquema nuevo), `documents/models.py`, portal del proveedor (comportamiento idéntico).

## Phase 0: Outline & Research

**Completado** → [research.md](research.md)

Resuelve siete puntos: qué existe ya (R1), dónde vive la regla de autoría respetando la convención del proyecto (R2), cómo compartir la regla de estado de celda sin ciclo de imports (R3), por qué `can_delete` lo calcula el servidor y no el cliente (R4), por qué el aislamiento multi-tenant ya está cubierto (R5), el tratamiento de documentos verificados y la ventana de gracia (R6), y el patrón de UI destructiva a reutilizar (R7).

## Phase 1: Design & Contracts

**Completado** → [data-model.md](data-model.md), [contracts/documents-delete.md](contracts/documents-delete.md), [quickstart.md](quickstart.md)

### Diseño del backend

1. **`compliance/cell_locks.py`** — `check_cell_unlocked(db, *, organization_id, supplier_id, document_type_id, coverage_period_start)`. Traslado literal de `portal/routes_write.py:286`. Lanza `Conflict("delete_not_allowed")` si la celda está enviada a validación o validada.

2. **`service.delete_document()`** — nuevo parámetro `require_owner: bool = False`.

   > **Ajuste durante la implementación**: el plan preveía pasar `actor_role: str` y que el
   > servicio dedujera la regla del rol. Se cambió a un booleano explícito porque el portal
   > del proveedor también llama a este servicio y allí la semántica es distinta: el
   > proveedor borra por celda, no por autoría (un documento cargado por el back-office
   > para su empresa sigue siendo borrable por él). Con `actor_role` el servicio tendría
   > que conocer la política de cada canal; con `require_owner` cada canal declara la suya
   > y la comprobación sigue viviendo dentro del servicio, que es lo que el principio I
   > exige. Por la misma razón, las reglas de "documento verificado" y "celda bloqueada"
   > quedaron en la ruta del back-office y no en el servicio: son de canal.

   Orden de comprobaciones, de la más barata a la más cara y de la menos a la más reveladora:
   1. documento inexistente o de otro tenant → `NotFound` (404)
   2. `require_owner` y `doc.uploaded_by != actor_user_id` → `Forbidden` (403, código `not_document_owner`)
   3. `doc.verified` → `Conflict` (409, código `document_verified`)
   4. ventana de gracia expirada → `Conflict` (409, `delete_window_expired`, ya existente)
   
   El resto del cuerpo —promoción de la versión previa, borrado físico, auditoría, `bump_tenant_version`— queda intacto.

3. **`documents/routes.py`** — `require_role(ADMIN, MANAGER)`, se pasa `require_owner=user.role != admin`, y se invoca `check_cell_unlocked()` **en la ruta** antes de llamar al servicio, según la convención de canal.

4. **`_serialize()`** — añade `can_delete: bool`. Es `True` cuando el usuario es admin, o es el autor con rol `manager`, y además el documento no está verificado y sigue dentro de la ventana. El estado de celda no entra en el cálculo del listado para no incurrir en N+1 (ver Constraints): si la celda está bloqueada, el botón aparece y la acción responde 409 con un mensaje claro — un caso de borde poco frecuente frente al coste de consultarlo por fila.

### Diseño del frontend

5. **`DocumentOut.can_delete`** en el tipo, y `documentsApi.remove(id)` sobre `DELETE /documents/{id}`.

6. **Botón "Eliminar"** en el footer del drawer, condicionado a `doc.can_delete`, con `DestructiveConfirmDialog` que nombra proveedor, tipo de documento y período y advierte que es irreversible.

7. **Tras el éxito**: invalidar las queries de documentos y de cumplimiento del proveedor, cerrar el drawer y mostrar el resultado sin recarga manual (FR-011).

### Orden de ejecución (Principio III)

Los tests de autorización van primero: contrato del 403/404/409/204 → aislamiento multi-tenant → implementación del backend → campo `can_delete` → UI.

## Phase 2: Task generation approach

`/speckit-tasks` debería producir tareas agrupadas por historia de usuario, en este orden de dependencia:

1. **Base compartida** (bloquea todo): mover `check_cell_unlocked`, verificar que el portal sigue verde con sus tests actuales.
2. **US2 — No poder borrar lo ajeno** (P1, seguridad primero): tests de contrato y de aislamiento, luego la regla de autoría en el servicio y la apertura del rol en la ruta.
3. **US1 — Corregir carga propia** (P1): `can_delete` en la respuesta, botón, diálogo, invalidación de queries, prueba E2E del flujo.
4. **US3 — Rastro de auditoría** (P2): verificar que `DOCUMENT_DELETED` ya alimenta el historial de la celda y que el enlace de descarga previo deja de servir el archivo; añadir test de regresión.

Las tareas de US2 y US1 no son paralelizables entre sí porque US1 consume el `can_delete` que US2 establece.

## Riesgos y decisiones abiertas

- **El admin sigue sujeto a la ventana de gracia de 24 h.** Es el comportamiento actual y esta feature no lo toca, pero conviene confirmarlo: si un admin debe poder borrar sin límite de tiempo, es un cambio aparte.
- **`can_delete` no consulta el estado de celda en el listado** (decisión de rendimiento, arriba). Consecuencia asumida: un botón visible que puede responder 409 en un caso poco frecuente.
- **Documento verificado**: la única salida es que un admin retire la verificación primero. Si el flujo real requiere que el autor pueda hacerlo, habría que revisar el permiso de `unverify`, que hoy es exclusivo de admin.
