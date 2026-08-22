# Research: Unificación de "Validado" y "Verificado"

**Feature**: 017-unify-verification | **Fecha**: 2026-08-21

Todas las incógnitas se resolvieron leyendo el código y midiendo los datos reales. No quedan marcadores NEEDS CLARIFICATION.

---

## R1 — Estado actual: dos mecanismos que nunca se hablaron

| | **Verificado** (documento) | **Validado** (celda) |
|---|---|---|
| Dónde se guarda | `documents.verified`, `verified_by`, `verified_at`, `verified_note` | tabla `compliance_cell_validations` |
| Endpoint | `POST /documents/{id}/verify` · `/unverify` | `POST /suppliers/{id}/compliance/validate` |
| Rol | verificar: admin+manager · **quitar: solo admin** | admin+manager |
| Reverso | sí | **no existe** |
| Auditoría | `document.verified` / `document.unverified` | **ninguna** — no escribe en `audit_log` |
| Nota | sí | no |
| UI | drawer de `/documents` (`VerifiedBadge`) | `DocumentViewerModal` desde la rejilla |

**Hallazgo**: `validate_document_type` (`compliance/routes.py:57`) sólo inserta o actualiza la fila de validación. No toca el documento, no audita y **no comprueba que exista un documento** en la celda.

---

## R2 — El documento vigente por celda es único

**Pregunta abierta del checklist**: si una celda admite varios documentos, ¿cuál porta la marca?

**Hallazgo**: no hay ambigüedad. `compliance/service.py:156-163` construye `docs_by_type_and_month` a partir de una consulta filtrada por `is_latest = True`, y `upload_document()` marca `prev_latest.is_latest = False` al subir una versión nueva. Hay **exactamente un documento vigente** por `(supplier, tipo, período)`. `document_count` cuenta también las versiones antiguas, pero sólo una es la vigente.

**Decisión**: la marca vive en el documento `is_latest` de la celda. La pregunta abierta queda cerrada sin necesidad de una regla nueva.

---

## R3 — Derivar el estado no cuesta consultas; ahorra una

**Preocupación de SC-005**: pasar de leer una tabla a derivar el estado podría penalizar la rejilla.

**Hallazgo**: ocurre lo contrario. `get_annual_compliance` ya carga el documento vigente de cada celda (`docs_by_type_and_month`) para calcular el estado. Derivar `is_type_validated` de `doc.verified` es **acceso a un atributo ya cargado**, cero consultas. Y elimina la consulta de `validation_rows` (`compliance/service.py:207-215`).

**Decisión**: la rejilla pasa de N+1 consultas a N. El criterio de rendimiento se cumple con margen.

---

## R4 — Un efecto secundario elegante sobre FR-009

**FR-009**: subir una versión nueva sobre una celda revisada debe dejarla pendiente.

**Hallazgo**: con el estado derivado esto es **automático y gratis**. El documento nuevo nace con `verified = False` y se convierte en el vigente; la celda pasa a mostrarse pendiente sin código adicional. Con el modelo actual la marca de celda persistía y la celda seguía diciendo "Validado" sobre evidencia que nadie había mirado — un fallo silencioso que esta feature corrige de paso.

**Decisión**: no se implementa nada para FR-009; se cubre con un test que lo fije como comportamiento esperado.

---

## R5 — Los dos motivos de rechazo del borrado se colapsan en uno

**Contexto**: la feature 016 rechaza el borrado por dos causas distintas: `document_verified` (documento verificado) y `delete_not_allowed` (celda validada).

**Hallazgo**: al unificar, ambas condiciones pasan a ser **la misma**. `check_cell_unlocked` (`compliance/cell_locks.py`) conserva sólo la comprobación de envío pendiente del proveedor, que sigue siendo independiente.

**Decisión**: se mantiene `document_verified` como único código de rechazo por revisión, y `delete_not_allowed` queda reservado para el envío pendiente del portal. Simplifica el contrato de 016 en lugar de complicarlo.

**Consecuencia en el portal**: `portal_delete_document` deja de rechazar por "celda validada" y pasa a rechazar por "documento vigente verificado". Tras la unificación son la misma condición, así que el proveedor no percibe cambio alguno.

### Ampliación descubierta durante la implementación

`cell_locks` **no era el único lector** de la tabla. El portal la consultaba en dos sitios más, que el análisis inicial no cubrió:

| Lugar | Regla | Riesgo si no se corrige |
|---|---|---|
| `portal/routes_write.py:178` (`portal_submit`) | no reenviar una celda ya validada | el proveedor podría reenviar celdas validadas |
| `portal/routes_write.py:313` (`_check_upload_allowed`) | no subir sobre una celda ya validada | el proveedor podría sobrescribir evidencia dada por buena |

Ambas leían `ComplianceCellValidation`, que tras la migración deja de recibir escrituras: habrían dejado de bloquear en silencio. Se corrigieron para leer el documento vigente verificado, conservando el mismo código de error y el mismo comportamiento observable. Sus dos tests (`test_upload_rejects_validated_cell`, `test_submit_rejects_validated_cell`) se adaptaron a construir el estado por el camino nuevo.

**Lección para el plan**: al retirar una fuente de verdad hay que buscar *todos* sus lectores, no sólo los del camino que motivó el cambio. `grep -rn "ComplianceCellValidation" backend/src` es la comprobación que lo habría detectado antes.

---

## R6 — Los datos existentes: medición real

Medido sobre la base de desarrollo:

| Situación | Filas |
|---|---|
| Validaciones de celda totales | 45 |
| …con documento vigente que migrar | **12** |
| …**sin ningún documento** (celdas vacías validadas) | **32** |
| …con documentos, pero todos borrados | 1 |
| Documentos verificados sin fila de validación | 3 |

Las 32 huérfanas son todas del proveedor Prov6 y se crearon en el mismo segundo (2026-06-08 16:56:14): una validación en bloque de celdas vacías, posible gracias a que el endpoint nunca exigió evidencia.

**Decisión (tomada con el usuario)**: **descartarlas**. Son exactamente el artefacto que FR-005 prohíbe crear en adelante, y una marca de "revisado" sin nada que revisar no es información recuperable. La migración debe **dejar constancia** de cuáles se descartan, no borrarlas en silencio.

**Decisión**: los 3 documentos verificados sin fila de validación no requieren nada — al derivar el estado, sus celdas pasan a mostrarse revisadas automáticamente. Es el otro lado de la divergencia, y se arregla solo.

**Alternativa descartada**: conservar la tabla viva para las celdas sin documento. Dejaría dos fuentes de verdad —el problema que la feature viene a eliminar— a cambio de preservar marcas sin respaldo.

---

## R7 — Qué hacer con la tabla `compliance_cell_validations`

**Decisión**: la migración copia los datos aprovechables a `documents` y **deja la tabla en su sitio, sin lectores ni escritores**, marcada como obsoleta en el modelo.

**Rationale**: la migración de datos es la parte irreversible; eliminar la tabla en el mismo paso convierte un error de migración en pérdida definitiva. Dejarla inerte permite verificar el resultado en producción y retirarla después con una migración trivial.

**Alternativa descartada**: `DROP TABLE` en la misma migración. Más limpio de leer, pero sin red de seguridad para un cambio que toca evidencia de cumplimiento.

---

## R8 — El término único de la interfaz (FR-011)

**Decisión**: la interfaz dice **"Validado"** en toda la aplicación; el dato interno sigue llamándose `verified`.

**Rationale**: "Validado" ya es el término de la rejilla de cumplimiento —la vista más usada y la única que ve el proveedor— y `CellStatus.VALIDATED` está publicado en los contratos de la API y consumido por el portal. Renombrar el enum de estado tendría un radio de impacto mucho mayor que renombrar un badge.

Separar el lenguaje de producto del nombre técnico de la columna evita una migración de esquema que no aporta nada al usuario: nadie fuera del código ve la palabra `verified`.

**Alternativa descartada**: renombrar `documents.verified` a `validated`. Migración de columna, cambios en modelos, schemas, tests y contratos, a cambio de coherencia interna que ningún usuario percibe. Contradice el principio IV.

---

## R9 — El permiso de retirar la revisión

**Decisión (tomada con el usuario)**: administrador **y gestor** pueden retirar la revisión.

Supone relajar la regla actual, donde `/unverify` es exclusivo del administrador (`documents/routes.py:218-221`). Se acepta para que ambas pantallas se comporten igual y para que el gestor pueda deshacer su propio error sin escalar.

**A señalar en la revisión del PR**: es la única relajación de control de esta feature. Todo lo demás endurece o deja igual.
