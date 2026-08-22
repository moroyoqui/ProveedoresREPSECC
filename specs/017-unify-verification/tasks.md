---

description: "Task list for 017 — Unificación de Validado y Verificado"
---

# Tasks: Unificación de "Validado" y "Verificado"

**Input**: Design documents from `/specs/017-unify-verification/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/verification.md](contracts/verification.md)

**Tests**: SÍ se incluyen tareas de test. La constitución (Principio III) exige tests antes del merge para autorización y aislamiento de tenant, y esta feature toca ambos; además la migración altera evidencia de cumplimiento de forma parcialmente irreversible, lo que no se toca sin red.

**Organization**: agrupadas por historia. US1 y US2 comparten archivos y se secuencian; US3 (migración) es independiente de la UI y se valida contra la base de datos.

**Dependencia externa**: esta feature reduce `backend/src/repse/compliance/cell_locks.py`, creado en la feature **016**. Si 016 no está mergeada, partir de ella.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede correr en paralelo (archivo distinto, sin dependencia pendiente)
- **[Story]**: historia a la que pertenece (US1, US2, US3)
- Toda tarea lleva ruta de archivo exacta

## Path Conventions

Aplicación web: `backend/src/repse/`, `backend/alembic/versions/`, `backend/tests/`, `frontend/src/`.

---

## Phase 1: Setup

**Purpose**: fotografiar el estado de partida. La migración de US3 se compara contra estos números, así que medir **antes** no es opcional.

- [X] T001 Registrar el conteo de partida (validaciones totales, con documento vigente, huérfanas, documentos verificados) ejecutando el bloque SQL de "Antes de migrar" de [quickstart.md](quickstart.md), y anotar el resultado en el PR
- [X] T002 Verificar la suite en verde antes de tocar nada: `pytest backend/tests -q` desde la raíz con `backend/.venv` y Docker levantado

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: cambiar el origen del estado de la celda. Bloquea todo porque redefine qué significa "validado" en el sistema entero.

**⚠️ CRITICAL**: hasta que esto no esté, cualquier trabajo sobre las historias opera con la semántica vieja.

- [X] T003 Escribir en `backend/tests/integration/test_verification_unification.py` el test que fija la derivación: un documento vigente con `verified=True` hace que su celda salga con `type_validated=True` en `GET /suppliers/{id}/compliance`, y con `verified=False` sale en `False` — debe **fallar** antes de T004
- [X] T004 En `backend/src/repse/compliance/service.py:277`, derivar `is_type_validated = doc is not None and doc.verified` y eliminar la consulta de `validation_rows` y el conjunto `validated_cells` (líneas 206-218), conservando intactos `CellOut.type_validated` y `CellStatus.VALIDATED`
- [X] T005 Aplicar la misma derivación a la rama de tipos sin periodicidad (`Periodicity.NONE`) en `backend/src/repse/compliance/service.py:257-266`, que hoy no consulta validaciones y quedaría incoherente con la rama mensual
- [X] T006 Reducir `backend/src/repse/compliance/cell_locks.py` a la comprobación de `PortalSubmission` pendiente, eliminando la de `ComplianceCellValidation` porque ahora es la misma condición que `document_verified` (ver [research.md](research.md) R5)
- [X] T007 Ajustar `backend/tests/contract/test_documents_delete_contract.py::test_cannot_delete_when_cell_is_validated` a la semántica nueva: la celda se bloquea porque su documento vigente está verificado, con código `document_verified` en lugar de `delete_not_allowed`
- [X] T008 Confirmar que el portal no cambia de comportamiento observable: `pytest backend/tests/test_portal_upload.py backend/tests/test_portal_isolation.py backend/tests/test_portal_submit.py -q`

**Checkpoint**: la rejilla ya lee del documento. Las dos pantallas no pueden divergir aunque nada más haya cambiado.

---

## Phase 3: US1 — Una sola marca, coherente en toda la aplicación (P1) ⭐ MVP

**Story goal**: que validar desde la rejilla y verificar desde documentos sean el mismo acto, escrito en el mismo sitio.

**Independent test**: validar una celda desde la rejilla y comprobar que el documento figura validado en `/documents` con el mismo autor y fecha; y a la inversa.

**Depends on**: Phase 2.

### Tests primero

- [X] T009 [P] [US1] Añadir a `backend/tests/integration/test_verification_unification.py` el caso de ida: `POST /suppliers/{id}/compliance/validate` deja el documento vigente con `verified=True`, `verified_by` del actor y `verified_at`
- [X] T010 [P] [US1] Añadir el caso de vuelta: `POST /documents/{id}/verify` hace que la celda salga `type_validated=True` en la rejilla sin ninguna acción adicional
- [X] T011 [P] [US1] Añadir el caso 422 `no_document_to_validate`: validar una celda sin documento vigente se rechaza (FR-005)
- [X] T012 [P] [US1] Añadir el caso de auditoría: validar desde la rejilla escribe un evento `document.verified` en `audit_log` con el actor correcto — hoy no escribe nada (FR-008)
- [X] T013 [P] [US1] Añadir el caso de FR-009: subir una versión nueva sobre una celda validada la devuelve a no validada, porque el documento nuevo es el vigente y nace sin verificar
- [X] T014 [US1] Añadir el caso negativo cross-tenant en `backend/tests/integration/test_tenant_isolation.py`: validar una celda de un proveedor de otra organización responde 404

### Implementación

- [X] T015 [US1] Reescribir `validate_document_type` en `backend/src/repse/compliance/routes.py:57` para que localice el documento vigente de la celda y delegue en `documents.service.verify_document()`, en lugar de insertar en `compliance_cell_validations`
- [X] T016 [US1] Añadir a esa ruta el rechazo `422 no_document_to_validate` cuando la celda no tiene documento vigente no borrado (FR-005)
- [X] T017 [US1] Aceptar `note` opcional en `ValidateCellIn` y propagarla a `verify_document()` (FR-012), y devolver `document_id` en la respuesta según [contracts/verification.md](contracts/verification.md)
- [X] T018 [P] [US1] Actualizar los tipos y la llamada de `validateDocumentType` en `frontend/src/lib/api/documents.ts:75` para el cuerpo y la respuesta nuevos
- [X] T019 [US1] Invalidar tras validar, en `frontend/src/components/documents/DocumentViewerModal.tsx:156`, las queries `documents-list`, `supplier-compliance` y `dashboard`, para que la coherencia se vea sin recargar (SC-001)
- [X] T020 [US1] Mostrar el motivo del rechazo `no_document_to_validate` en el visor en lugar del mensaje genérico "No se pudo validar el tipo de documento" de `DocumentViewerModal.tsx:163`

**Checkpoint**: MVP. El fallo reportado (Prov1 · Cédula cuota IMSS · julio 2026) ya no puede reproducirse con datos nuevos.

---

## Phase 4: US2 — Retirar la revisión (P1)

**Story goal**: dar marcha atrás desde cualquiera de las dos pantallas. Hoy la validación de celda es irreversible.

**Independent test**: retirar la revisión y comprobar que ambas pantallas dejan de mostrarla, con el retiro registrado en el historial.

**Depends on**: Phase 3 (comparte ruta y componentes con US1).

### Tests primero

- [X] T021 [P] [US2] Añadir a `backend/tests/integration/test_verification_unification.py` el caso 200 de `POST /suppliers/{id}/compliance/unvalidate`: el documento vigente queda sin verificar y la celda deja de salir validada
- [X] T022 [P] [US2] Añadir el caso 403: un `viewer` no puede validar ni retirar por ninguna de las dos rutas (FR-007)
- [X] T023 [P] [US2] Añadir el caso de permiso ampliado: un `manager` puede ejecutar `POST /documents/{id}/unverify`, que hoy responde 403 (FR-007) — debe **fallar** antes de T026
- [X] T024 [P] [US2] Añadir el caso idempotente: retirar la revisión de una celda cuyo documento no estaba verificado responde 200 sin efecto — `unverify_document()` ya lo resuelve sin error y no se le añade un 409 nuevo
- [X] T025 [P] [US2] Añadir el caso de auditoría del retiro: consta `document.unverified` con autor y fecha, sin borrar el registro de la revisión previa (FR-008)

### Implementación

- [X] T026 [US2] Cambiar `unverify_document_route` en `backend/src/repse/documents/routes.py:218` de `require_role(ADMIN)` a `require_role(ADMIN, MANAGER)` (FR-007) — **única relajación de control de la feature; señalar en el PR**
- [X] T027 [US2] Añadir `POST /suppliers/{supplier_id}/compliance/unvalidate` en `backend/src/repse/compliance/routes.py`, delegando en `documents.service.unverify_document()` sobre el documento vigente, con los códigos de [contracts/verification.md](contracts/verification.md)
- [X] T028 [P] [US2] Añadir `unvalidateDocumentType` a `frontend/src/lib/api/documents.ts` junto a `validateDocumentType`
- [X] T029 [US2] Añadir el control de retirar validación en `frontend/src/components/documents/DocumentViewerModal.tsx`, junto al de validar, gobernado por el estado del documento vigente
- [X] T030 [US2] Habilitar "Quitar validación" al gestor en `frontend/src/components/documents/DocumentDetailDrawer.tsx:53` y en `frontend/src/pages/documents/list.tsx:208`, donde hoy la condición es `user?.role === "admin"`

**Checkpoint**: la marca ya no es una vía de sentido único.

---

## Phase 5: US3 — El histórico queda coherente (P2)

**Story goal**: que los datos ya existentes dejen de contradecirse, incluido el caso que originó la petición.

**Independent test**: tras migrar, ninguna celda con documento vigente queda sin alinear (consulta de comprobación en [quickstart.md](quickstart.md)).

**Depends on**: Phase 2. Independiente de US1 y US2 — se valida contra la base de datos.

- [X] T031 [P] [US3] Escribir `backend/tests/integration/test_migration_unify_validation.py` con el caso de traslado: una validación de celda con documento vigente sin verificar deja el documento con `verified=True` y **conserva** `validated_by` y `validated_at` originales
- [X] T032 [P] [US3] Añadir el caso de no pisar: si el documento ya estaba verificado, la migración respeta su autoría y su fecha
- [X] T033 [P] [US3] Añadir el caso de descarte: una validación sin documento vigente no crea nada y **queda registrada** en la salida de la migración (FR-010, [research.md](research.md) R6)
- [X] T034 [P] [US3] Añadir el caso de aislamiento: la migración itera por organización y no cruza datos entre tenants (Principio II)
- [X] T035 [US3] Crear `backend/alembic/versions/0013_unify_cell_validation_into_documents.py` con la lógica de [data-model.md](data-model.md): trasladar las validaciones con documento vigente, registrar las descartadas, y **no eliminar** `compliance_cell_validations` (R7)
- [X] T036 [US3] Marcar `ComplianceCellValidation` como obsoleta en `backend/src/repse/compliance/models.py:22` con un comentario que apunte a esta feature y advierta de que no debe leerse ni escribirse
- [X] T037 [US3] Ejecutar la migración sobre la base de desarrollo y comprobar los números esperados: 12 trasladadas, 33 descartadas y registradas, 0 celdas con documento vigente sin alinear

**Checkpoint**: el histórico ya no contiene contradicciones.

---

## Phase 6: Término único en la interfaz (FR-011)

**Purpose**: que el usuario vea **una sola palabra**. Va al final a propósito: es cosmético comparado con la coherencia de datos, y hacerlo antes obligaría a repasar los mismos archivos dos veces.

- [X] T038 [P] Cambiar "Verificado" / "Sin verificar" por "Validado" / "Sin validar" en `frontend/src/components/documents/VerifiedBadge.tsx`
- [X] T039 [P] Cambiar "Verificar documento" y "Quitar verificación" por "Validar documento" y "Quitar validación" en `frontend/src/components/documents/DocumentDetailDrawer.tsx:310,320` y `frontend/src/pages/documents/list.tsx:208`
- [X] T040 [P] Cambiar "Marcar como verificado" por "Marcar como validado" en `frontend/src/components/documents/VerifyDialog.tsx:37,46`
- [X] T041 [P] Cambiar las etiquetas del filtro "Verificado" a "Validado" en `frontend/src/components/documents/DocumentFiltersBar.tsx:64-76`, sin tocar el nombre del parámetro de consulta
- [X] T042 Ajustar el mensaje de rechazo `document_verified` en `frontend/src/components/documents/DocumentDetailDrawer.tsx:69` al término único
- [X] T043 Comprobar que no queda "verificad" visible al usuario: `grep -rniE "verificad" frontend/src --include=*.tsx` sólo debe devolver nombres de variables y comentarios, no textos renderizados. **Ampliado**: los resúmenes del historial (`_HUMAN_SUMMARIES` en `backend/src/repse/documents/routes.py`) también son texto de usuario y se unificaron — el grep del frontend no los alcanzaba

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T044 [P] Recorrer los nueve pasos de verificación manual de [quickstart.md](quickstart.md), incluido el caso concreto de Prov1 · Cédula cuota IMSS · julio 2026 — verificado por API contra la app en Docker; los roles gestor/consultor los cubren los tests (no hay esas cuentas en dev)
- [X] T045 [P] Comprobar que la rejilla no consulta `compliance_cell_validations` en ningún camino: `grep -rn "ComplianceCellValidation" backend/src` sólo debe aparecer en el modelo y en la migración
- [X] T046 [P] Medir que `GET /suppliers/{id}/compliance` no empeoró y que hace una consulta menos que antes (SC-005)
- [X] T047 Repasar los cinco puntos de "Qué revisar en code review" de [quickstart.md](quickstart.md) antes de abrir el PR — los cinco pasan
- [X] T048 Ejecutar la suite completa: `pytest backend/tests -q`, `cd frontend && npm run test` y `npx tsc --noEmit`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias; T001 debe hacerse **antes** de cualquier migración
- **Foundational (Phase 2)**: bloquea todo — redefine el origen del estado
- **US1 (Phase 3)**: depende de Phase 2
- **US2 (Phase 4)**: depende de Phase 3 — comparte ruta (`compliance/routes.py`) y componente (`DocumentViewerModal`)
- **US3 (Phase 5)**: depende de Phase 2; **paralela** a US1 y US2
- **Término único (Phase 6)**: depende de US1 y US2 (toca los mismos componentes)
- **Polish (Phase 7)**: al final

### Nota sobre independencia

US1 y US2 no son independientes entre sí: el reverso opera sobre el mismo endpoint y el mismo componente que la marca. US3 sí lo es y puede repartirse a otra persona desde el checkpoint de Phase 2.

### Within Each User Story

- Los tests se escriben y **fallan** antes de implementar (Principio III)
- Servicio antes que ruta; backend antes que UI; datos antes que cosmética

### Parallel Opportunities

- T009–T013 son casos del mismo archivo: paralelizables si se reparten como funciones; T014 toca otro archivo y es paralelo de verdad
- T031–T034 igual, sobre el archivo de la migración
- **Phase 5 completa** es paralela a Phase 3 y Phase 4
- Phase 6 es cuatro tareas [P] en archivos distintos

---

## Parallel Example: tras el checkpoint de Phase 2

```bash
# Dos frentes que no se pisan:
Task: "US1 + US2 — endpoints, reverso y UI (compliance/routes.py, DocumentViewerModal, drawer)"
Task: "US3 — migración y sus tests (alembic/versions/, test_migration_unify_validation.py)"
```

---

## Implementation Strategy

### MVP

Phases 1 → 2 → 3. Con eso el fallo reportado deja de ser reproducible sobre datos nuevos: ambas pantallas escriben y leen del mismo sitio. **Parar y validar** antes de seguir.

### Entrega incremental

1. Phase 2 → la rejilla deriva del documento; coherencia garantizada, sin cambios visibles de flujo
2. Phase 3 → MVP: una sola acción, auditada, que exige evidencia
3. Phase 4 → el reverso que faltaba
4. Phase 5 → histórico alineado (**avisar antes**: 32 celdas de Prov6 pasan a "Faltante")
5. Phase 6 → una sola palabra en la interfaz

### Aviso de despliegue

Phase 5 tiene efecto visible e irreversible en lo que muestra la rejilla. No desplegarla sin avisar a quien use la vista de cumplimiento de Prov6.
