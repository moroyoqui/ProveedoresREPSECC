# Data Model: Borrado de Documentos Propios en el Back-Office

**Feature**: 016-own-document-delete | **Fecha**: 2026-08-21

## Resumen

**No hay cambios de esquema ni migración Alembic.** Todos los datos que la feature necesita ya están persistidos. Lo único nuevo es un campo **derivado** en la respuesta de la API.

---

## Entidades involucradas (existentes, sin modificar)

### Document — `backend/src/repse/documents/models.py:45`

Campos que la feature consulta:

| Campo | Tipo | Papel en esta feature |
|---|---|---|
| `uploaded_by` | FK → `users.id` | **Clave de la feature**: identifica al autor de la carga; se compara con el usuario autenticado |
| `organization_id` | FK → `organizations.id` | Aislamiento multi-tenant, aplicado por el filtro ORM global |
| `created_at` | datetime | Origen del cómputo de la ventana de gracia |
| `verified` | bool | Bloquea el borrado cuando es `True` |
| `deleted_at` | datetime \| null | Marca del soft-delete; se fija al borrar |
| `is_latest` | bool | Se pone en `False`; la versión previa se promueve a vigente |
| `version` | int | Determina qué versión previa se promueve |
| `supplier_id`, `document_type_id`, `coverage_period_start` | — | Identifican la celda de cumplimiento cuyo bloqueo se consulta |
| `file_path` | str | Archivo físico que se elimina del disco |

### User — `backend/src/repse/users/models.py`

Se usa `id` (comparado con `uploaded_by`) y `role` (`admin` \| `manager` \| `viewer` \| `supplier`). El rol `viewer` no alcanza la ruta: `require_role` lo rechaza antes.

### PortalSubmission / ComplianceCellValidation

Consultadas en modo lectura por `check_cell_unlocked()` para saber si la celda está enviada a validación o ya validada. Sin cambios.

### AuditEvent

Recibe un asiento `document.deleted` con `actor_user_id`, `entity_id` y metadata (`reason`, `file_path`, `promoted_previous_latest_id`). Ya lo escribe `service.delete_document()`; no se modifica.

---

## Campo derivado nuevo

### `DocumentOut.can_delete: bool`

Calculado en `_serialize()` en cada respuesta; **no se persiste**.

```
can_delete = (rol == admin  OR  (rol == manager  AND  uploaded_by == usuario_actual))
             AND  NOT verified
             AND  (ahora - created_at) <= document_delete_grace_hours
```

El estado de la celda queda deliberadamente fuera del cálculo, por rendimiento en el listado (ver [plan.md](plan.md), Constraints). El servidor sigue verificándolo al ejecutar el borrado.

---

## Reglas de validación (derivadas de los FR)

| Regla | Origen | Respuesta al incumplirse |
|---|---|---|
| El documento existe y pertenece al tenant del solicitante | FR-004, Principio II | `404 Document not found` |
| El solicitante es el autor, o es admin | FR-001, FR-002, FR-004 | `403 not_document_owner` |
| El rol permite borrar (no `viewer`, no `supplier`) | FR-007 | `403` desde `require_role` |
| El documento no está verificado | FR-006 | `409 document_verified` |
| La celda no está enviada a validación ni validada | FR-006 | `409 delete_not_allowed` |
| El documento está dentro de la ventana de gracia | FR-005 | `409 delete_window_expired` |

Un tenant ajeno recibe `404` y no `403`: revelar "existe pero no es tuyo" filtraría información entre organizaciones.

---

## Transiciones de estado

**Del documento**:

```
activo (deleted_at = NULL, is_latest = true|false)
   │
   └─ borrado ─→ eliminado (deleted_at = ahora, is_latest = false)
                 └─ efecto lateral: la versión previa del mismo
                    (supplier, tipo, período), si existe, pasa a is_latest = true
```

Es terminal: no hay transición de vuelta. El archivo físico se elimina del disco (best-effort) y la fila permanece para auditoría.

**De la celda de cumplimiento**: tras el borrado, el estado se recalcula sobre la versión promovida o, si no hay ninguna, vuelve a "Faltante" (FR-008). `bump_tenant_version()` invalida la caché del tablero.
