# Research: Borrado de Documentos Propios en el Back-Office

**Feature**: 016-own-document-delete | **Fecha**: 2026-08-21

Todas las incógnitas se resolvieron leyendo el código existente; no quedan marcadores NEEDS CLARIFICATION.

---

## R1 — Punto de partida: qué existe ya

**Hallazgo**: el borrado en el back-office **ya está implementado en el backend** y sólo le falta permiso y superficie de UI.

| Pieza | Estado actual | Ubicación |
|---|---|---|
| Endpoint `DELETE /documents/{id}` | Existe, restringido a `admin` | `backend/src/repse/documents/routes.py:236` |
| `service.delete_document()` | Soft-delete + borrado físico + promoción de versión previa + auditoría + `bump_tenant_version` | `backend/src/repse/documents/service.py:334` |
| Ventana de gracia | `document_delete_grace_hours`, 24 h por defecto | `backend/src/repse/config.py:53` |
| Autor de la carga | `Document.uploaded_by` (FK a `users`) | `backend/src/repse/documents/models.py:115` |
| Botón en la UI administrativa | **No existe** | ausente en `frontend/src/pages/documents/list.tsx` y `components/documents/` |

**Decisión**: la feature es un **delta de permiso + UI**, no una funcionalidad nueva. No se reescribe `delete_document`; se le añade la verificación de autoría.

**Alternativa descartada**: crear un endpoint separado `DELETE /documents/{id}/own`. Duplicaría la lógica de borrado y dejaría dos caminos que mantener en sincronía. Un solo endpoint con la regla de autoría dentro es más simple (Principio IV).

---

## R2 — Dónde vive la regla de autoría: ¿ruta o servicio?

**Contexto**: `documents/service.py` es capa compartida entre el back-office y el portal del proveedor. La docstring de `portal/routes_write.py:1-14` fija la convención del proyecto de forma explícita:

> "Ambos llaman a documents/service.upload_document() como capa de servicio compartida. Agregar lógica exclusiva de un canal debe quedar en su ruta, NO dentro del service."

**Decisión**: la regla "sólo el autor, salvo admin" es **común a ambos canales conceptualmente pero se expresa distinto** (el portal ya restringe por proveedor y por estado de celda). Se implementa así:

- La comprobación **autor vs. rol** entra en `service.delete_document()` mediante un parámetro nuevo `actor_role`, porque es una regla sobre el documento mismo, no sobre el canal, y debe aplicarse aunque el llamador se equivoque.
- La comprobación **estado de celda** (enviada a validación / validada) se extrae del portal a un helper neutral reutilizable, y **cada ruta lo invoca**, respetando la convención citada.

**Alternativa descartada**: poner la autoría sólo en la ruta del back-office. Dejaría el servicio como un camino sin protección para cualquier llamador futuro; la constitución (Principio I) pide autorización aplicada en la capa que persiste, no sólo en el borde.

---

## R3 — Reutilizar `_check_delete_allowed` sin crear un ciclo de imports

**Contexto**: la función vive hoy en `portal/routes_write.py:286` y consulta `PortalSubmission` (`portal/models.py`) y `ComplianceCellValidation` (`compliance/models.py`). El back-office no puede importar del paquete `portal` sin invertir la dirección de dependencia que hoy va portal → documents.

**Decisión**: mover la función a un módulo neutral **`backend/src/repse/compliance/cell_locks.py`**, con el nombre `check_cell_unlocked()`. Ambas rutas la importan.

- No hay ciclo: `compliance/cell_locks.py` importa `portal/models.py` y `compliance/models.py` (módulos de modelos, sin lógica de rutas); `portal/routes_write.py` importa `compliance/cell_locks`.
- El movimiento es un desplazamiento literal de la función existente, sin cambios de comportamiento, para no alterar lo que ya funciona en el portal.

**Alternativas descartadas**:
- Duplicar la consulta en `documents/`: dos copias de una regla de negocio que deben cambiar juntas.
- Import diferido dentro de la función (`import` local): esconde la dependencia y complica el testeo.

---

## R4 — Cómo sabe la UI si puede mostrar el botón

**Contexto**: el frontend ya recibe `audit.added.user.id` en `DocumentOut` (`frontend/src/lib/api/index.ts:361-386`) y conoce al usuario autenticado vía `useAuth()` (`frontend/src/lib/auth.tsx`). Podría decidir por sí solo comparando ambos ids.

**Decisión**: el backend expone un campo booleano **`can_delete`** en `DocumentOut`, calculado por el servidor.

**Rationale**: la visibilidad del botón depende de cuatro condiciones —autoría, rol, ventana de gracia y estado de celda—, y tres de ellas el cliente no puede evaluar de forma fiable (la ventana depende de la hora del servidor y de una variable de configuración; el estado de celda no viaja en el payload del documento). Recalcularlas en el cliente produciría botones que aparecen y fallan al pulsarlos. El servidor ya tiene todos los datos.

**Alternativa descartada**: comparar `audit.added.user.id === user.id` en el cliente. Simple, pero muestra el botón sobre documentos vencidos de ventana o con celda bloqueada, convirtiendo un caso previsible en un error al confirmar — justo lo que SC-001 quiere evitar.

---

## R5 — Aislamiento multi-tenant

**Hallazgo**: no hace falta añadir un filtro por `organization_id` en la ruta de borrado. El listener `do_orm_execute` de `backend/src/repse/db/tenant_filter.py:66` inyecta `organization_id = :current_tenant` en toda consulta ORM sobre modelos `TenantOwned`, y `current_user` fija el tenant por petición (`auth/dependencies.py:44`). `Document` hereda de `TenantOwned`.

**Decisión**: apoyarse en el mecanismo existente y **cubrirlo con un test negativo explícito** (Principio II exige la prueba del caso negativo), en lugar de duplicar la condición en la ruta.

---

## R6 — Verificado y ventana de gracia

**Decisión**: se rechaza el borrado de un documento `verified = True`, incluso para su autor y dentro de la ventana. Un documento verificado es evidencia que otra persona ya revisó; retirarla requiere primero `POST /documents/{id}/unverify`, que ya existe y es exclusivo de admin (`routes.py:218-221`).

**Decisión**: se reutiliza `document_delete_grace_hours` sin introducir un plazo distinto para el borrado propio. Dos relojes de caducidad conviviendo sobre la misma acción es complejidad sin demanda (Principio IV).

**Nota sobre el admin**: hoy el admin también está sujeto a la ventana de gracia, porque la ruta pasa `grace_hours=settings.document_delete_grace_hours`. Esta feature **no cambia** ese comportamiento.

---

## R7 — Patrón de UI para la confirmación destructiva

**Hallazgo**: el proyecto ya tiene `frontend/src/components/ui/DestructiveConfirmDialog.tsx`, usado para el cambio de tipo de proveedor, y las acciones por documento viven en dos sitios: los botones por fila de `pages/documents/list.tsx:160-200` y el bloque "Footer actions" de `components/documents/DocumentDetailDrawer.tsx:244-265`, donde ya conviven "Verificar" y "Quitar verificación" con su propia lógica de permiso (`canVerify`, `canUnverify`).

**Decisión**: el botón "Eliminar" se suma al footer del drawer siguiendo el patrón de `canUnverify`, gobernado por el nuevo `can_delete`, y reutiliza `DestructiveConfirmDialog` en lugar de un `confirm()` del navegador.

**Alternativa descartada**: añadirlo también como botón por fila en la tabla. Multiplica la superficie de una acción irreversible sin que el usuario tenga el contexto del documento a la vista. Queda fuera de alcance.
