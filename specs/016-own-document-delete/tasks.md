---

description: "Task list for 016 — Borrado de Documentos Propios en el Back-Office"
---

# Tasks: Borrado de Documentos Propios en el Back-Office

**Input**: Design documents from `/specs/016-own-document-delete/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/documents-delete.md](contracts/documents-delete.md)

**Tests**: SÍ se incluyen tareas de test. No es una preferencia de estilo: la constitución del proyecto (Principio III, *Test-First for Critical Paths*) exige tests automatizados **antes del merge** para la lógica de autorización y aislamiento de tenant, que es exactamente lo que esta feature toca.

**Organization**: agrupadas por historia de usuario. A diferencia del caso habitual, **US2 precede a US1**: la regla de permiso y el campo `can_delete` que produce US2 son lo que US1 consume para decidir si pinta el botón.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede correr en paralelo (archivo distinto, sin dependencia pendiente)
- **[Story]**: historia a la que pertenece (US1, US2, US3)
- Toda tarea lleva ruta de archivo exacta

## Path Conventions

Aplicación web: `backend/src/repse/`, `backend/tests/`, `frontend/src/`.

---

## Phase 1: Setup

**Purpose**: no hay inicialización que hacer — el proyecto, sus dependencias y el linting ya existen y esta feature no añade paquetes ni migraciones.

- [X] T001 Verificar que el entorno corre en verde antes de tocar nada: `pytest backend/tests/contract backend/tests/integration -q` desde la raíz con `backend/.venv` activo y Docker levantado

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: mover la regla de estado de celda a un lugar que ambos canales puedan compartir. Bloquea todas las historias porque la ruta del back-office la necesita y el portal no puede quedar roto en el intermedio.

**⚠️ CRITICAL**: ninguna historia empieza hasta que el portal siga verde con esta base.

- [X] T002 Crear `backend/src/repse/compliance/cell_locks.py` con `check_cell_unlocked(db, *, organization_id, supplier_id, document_type_id, coverage_period_start)`, trasladando **literalmente** el cuerpo de `_check_delete_allowed` de `backend/src/repse/portal/routes_write.py:286` (mismas consultas, mismo `Conflict` con `code="delete_not_allowed"`)
- [X] T003 Sustituir en `backend/src/repse/portal/routes_write.py` la función local `_check_delete_allowed` por el import de `check_cell_unlocked`, eliminando la definición huérfana y dejando la llamada de `portal_delete_document` apuntando al helper
- [X] T004 Confirmar que el portal no cambió de comportamiento: `pytest backend/tests/test_portal_upload.py backend/tests/test_portal_isolation.py backend/tests/test_portal_submit.py -q` debe pasar **sin modificar ningún test**

**Checkpoint**: helper compartido en su sitio, portal intacto.

---

## Phase 3: US2 — No poder borrar lo ajeno (P1) 🔒

**Story goal**: que la ampliación de permiso nazca acotada. Un gestor puede borrar lo suyo; lo de otro no, ni por la interfaz ni saltándosela.

**Independent test**: con dos usuarios distintos, cargar un documento con el primero y verificar con el segundo que un `DELETE` directo devuelve 403 y el documento sigue intacto.

### Tests primero (deben fallar antes de implementar)

- [X] T005 [P] [US2] Crear `backend/tests/contract/test_documents_delete_contract.py` con el caso 204: un `manager` borra el documento que él mismo subió y la fila queda con `deleted_at`
- [X] T006 [P] [US2] Añadir en el mismo archivo el caso 403: un `manager` intenta borrar un documento subido por otro usuario → `code: not_document_owner` y el documento permanece
- [X] T007 [P] [US2] Añadir el caso 403 de rol: un `viewer` recibe rechazo de `require_role` incluso sobre un documento que figura a su nombre
- [X] T008 [P] [US2] Añadir el caso 409 `document_verified`: el autor intenta borrar un documento ya verificado
- [X] T009 [P] [US2] Añadir el caso 409 `delete_window_expired`: documento del propio autor con `created_at` retrasado más allá de `document_delete_grace_hours`
- [X] T010 [P] [US2] Añadir el caso 409 `delete_not_allowed`: la celda del documento tiene un `PortalSubmission` pendiente o un `ComplianceCellValidation`
- [X] T011 [US2] Añadir a `backend/tests/integration/test_tenant_isolation.py` el caso negativo de borrado entre organizaciones: un admin de la org A recibe **404** (no 403) al borrar un documento de la org B, y la fila de B queda intacta

### Implementación

- [X] T012 [US2] Añadir el parámetro `actor_role: str` a `delete_document()` en `backend/src/repse/documents/service.py:334` y aplicar, en este orden, las comprobaciones de: documento inexistente (`NotFound`), autoría cuando `actor_role != admin` (`Forbidden`, `code="not_document_owner"`) y documento verificado (`Conflict`, `code="document_verified"`), antes de la ventana de gracia ya existente
- [X] T013 [US2] Actualizar la llamada de `backend/src/repse/portal/routes_write.py` a `delete_document()` para pasar `actor_role` con el rol del proveedor, comprobando que el portal conserva su semántica actual
- [X] T014 [US2] En `backend/src/repse/documents/routes.py:236`, abrir la ruta con `require_role(Role.ADMIN.value, Role.MANAGER.value)`, invocar `check_cell_unlocked()` **desde la ruta** (convención de `portal/routes_write.py:1-14`) y pasar `actor_role=user.role` al servicio
- [X] T015 [US2] Añadir el campo derivado `can_delete` en `_serialize()` de `backend/src/repse/documents/routes.py:350` según la fórmula de [data-model.md](data-model.md) (rol + autoría + no verificado + dentro de ventana), sin consultar el estado de celda para no incurrir en N+1
- [X] T016 [US2] Ejecutar `pytest backend/tests/contract/test_documents_delete_contract.py backend/tests/integration/test_tenant_isolation.py -q` y dejar los seis casos de contrato más el de aislamiento en verde

**Checkpoint**: el permiso está acotado y probado. La API ya es correcta aunque todavía no haya botón.

---

## Phase 4: US1 — Corregir una carga equivocada propia (P1) ⭐ MVP

**Story goal**: dar superficie visible a lo que US2 habilitó, para que el gestor corrija su error sin escalar a un administrador.

**Independent test**: un gestor sube un documento, lo abre desde `/documents`, usa Eliminar, confirma, y el documento desaparece del listado mientras la celda del proveedor recalcula su estado — todo sin recargar la página.

**Depends on**: Phase 3 (consume `can_delete` y el 403/409 del backend).

- [X] T017 [P] [US1] Añadir `can_delete: boolean` al tipo `DocumentOut` en `frontend/src/lib/api/index.ts:361`
- [X] T018 [P] [US1] Añadir `remove: (id: number) => Promise<void>` sobre `DELETE /documents/${id}` al objeto `documentsApi` de `frontend/src/lib/api/index.ts`, junto a `verify` y `unverify`
- [X] T019 [US1] Añadir el botón "Eliminar" al bloque *Footer actions* de `frontend/src/components/documents/DocumentDetailDrawer.tsx:244`, condicionado a `doc.can_delete` y siguiendo el patrón de `canUnverify` (variante destructiva, estado `isPending`)
- [X] T020 [US1] Conectar el botón a `DestructiveConfirmDialog` de `frontend/src/components/ui/DestructiveConfirmDialog.tsx`, con un texto que nombre proveedor, tipo de documento y período y advierta que la acción es irreversible (FR-003)
- [X] T021 [US1] Manejar los errores de la mutación en el drawer: mostrar el motivo devuelto para `document_verified`, `delete_not_allowed` y `delete_window_expired` en lugar de un mensaje genérico, reutilizando el patrón de `unverifyError`
- [X] T022 [US1] Tras el borrado exitoso, invalidar las queries de documentos y de cumplimiento del proveedor y cerrar el drawer desde `frontend/src/pages/documents/list.tsx`, de modo que el listado se actualice sin recarga manual (FR-011)
- [X] T023 [US1] Tratar el `404` posterior a un borrado propio como éxito silencioso (doble clic / doble confirmación) en el manejador de la mutación, sin mostrar error al usuario
- [X] T024 [P] [US1] Añadir prueba de componente en `frontend/tests/unit/document-delete-button.test.tsx` que cubra: botón visible con `can_delete: true`, ausente con `can_delete: false`, y que cancelar el diálogo no dispara la llamada

**Checkpoint**: MVP entregable. Las historias 1 y 2 juntas ya cumplen la petición original.

---

## Phase 5: US3 — Rastro de auditoría del borrado (P2)

**Story goal**: que el borrado propio no deje huecos inexplicables en la evidencia.

**Independent test**: borrar un documento propio y verificar que el historial de la celda muestra la eliminación con autor y fecha, y que un enlace de descarga previo ya no entrega el archivo.

**Depends on**: Phase 3. Independiente de la UI de US1 — se puede validar por API.

- [X] T025 [P] [US3] Añadir a `backend/tests/contract/test_documents_history_contract.py` el caso de que un borrado ejecutado por su autor aparece en el historial como `document.deleted` con el actor correcto y su marca temporal
- [X] T026 [P] [US3] Añadir un test de regresión que confirme que un token de descarga emitido **antes** del borrado deja de resolver el archivo después (FR-010), en `backend/tests/contract/test_documents_delete_contract.py`
- [X] T027 [US3] Verificar que `_HUMAN_SUMMARIES` de `backend/src/repse/documents/routes.py:260` cubre `DOCUMENT_DELETED` con un texto adecuado también cuando el autor no es admin, y ajustarlo si el resumen resulta engañoso
- [X] T028 [US3] Comprobar sobre datos reales que tras el borrado la celda refleja la versión promovida o "Faltante" (FR-008, SC-005), apoyándose en `bump_tenant_version` ya invocado por el servicio

**Checkpoint**: la eliminación es auditable de punta a punta.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Recorrer los nueve pasos de verificación manual de [quickstart.md](quickstart.md) con las cuatro cuentas (admin, dos managers, viewer)
- [X] T030 [P] Revisar que el listado de documentos no dispara consultas extra por fila al calcular `can_delete`, comparando el número de consultas antes y después sobre una página completa
- [X] T031 Repasar los cuatro puntos de "Qué revisar en code review" de [quickstart.md](quickstart.md) antes de abrir el PR
- [X] T032 Ejecutar la suite completa del backend y el lint: `pytest backend/tests -q` y `ruff check backend/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias
- **Foundational (Phase 2)**: bloquea todas las historias — la ruta del back-office necesita `check_cell_unlocked` y el portal no puede quedar a medias
- **US2 (Phase 3)**: depende de Phase 2
- **US1 (Phase 4)**: depende de **Phase 3**, no sólo de Phase 2 — consume `can_delete` y los códigos de error del backend
- **US3 (Phase 5)**: depende de Phase 3; puede correr en paralelo con Phase 4
- **Polish (Phase 6)**: depende de las historias que se decidan entregar

### Diferencia respecto al patrón habitual

Las historias de esta feature **no son mutuamente independientes**: US1 es la superficie visible de la regla que US2 establece. Se ordenan seguridad primero a propósito, para que no exista una ventana en la que el botón esté disponible sin la restricción de autoría detrás.

US3 sí es independiente de US1 y se valida por API.

### Within Each User Story

- Los tests se escriben y **fallan** antes de implementar (Principio III)
- Servicio antes que ruta; ruta antes que serialización; backend antes que UI

### Parallel Opportunities

- T005–T010 son casos del mismo archivo escritos como bloque: paralelizables entre sí sólo si se reparten como funciones separadas; T011 toca otro archivo y es paralelo de verdad
- T017 y T018 tocan el mismo archivo en secciones distintas: coordinar o hacer secuencial
- Phase 4 y Phase 5 son paralelizables entre dos personas una vez cerrada Phase 3

---

## Parallel Example: US2

```bash
# Los casos de contrato pueden repartirse entre dos personas si se acuerdan
# los helpers compartidos del archivo primero:
Task: "Casos 204 y 403 de autoría en backend/tests/contract/test_documents_delete_contract.py"
Task: "Casos 409 (verificado, ventana, celda) en el mismo archivo"

# Y en paralelo, en otro archivo:
Task: "Caso negativo cross-tenant en backend/tests/integration/test_tenant_isolation.py"
```

---

## Implementation Strategy

### MVP

Phases 1 → 2 → 3 → 4. Entrega la petición completa: botón visible sobre lo propio, invisible y rechazado sobre lo ajeno. **Parar y validar** con el quickstart antes de seguir.

### Entrega incremental

1. Phase 2 → helper compartido, sin cambio visible para nadie
2. Phase 3 → API correcta y probada; desplegable aunque no haya UI
3. Phase 4 → MVP a la vista del usuario
4. Phase 5 → auditoría reforzada

### Nota sobre el reparto

Con dos personas, el corte natural es después de Phase 3: una toma la UI (Phase 4) y otra la auditoría (Phase 5). Antes de ese punto el trabajo es demasiado acoplado para repartirlo sin pisarse.
