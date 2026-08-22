# Implementation Plan: Unificación de "Validado" y "Verificado"

**Branch**: `017-unify-verification` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-unify-verification/spec.md`

## Summary

Hoy conviven dos marcas de revisión que nunca se sincronizaron: `documents.verified` (por documento, con autoría, nota, auditoría y reverso) y la tabla `compliance_cell_validations` (por celda, sin auditoría, sin reverso y sin exigir evidencia). Pueden decir cosas contrarias sobre la misma evidencia, que es el fallo reportado.

El enfoque: **el documento pasa a ser la única fuente de verdad** y el estado de la celda se deriva de su documento vigente. La rejilla deja de consultar la tabla y lee `doc.verified`, que ya tiene cargado. El endpoint de validar celda se convierte en un atajo que verifica el documento vigente. Se añade el reverso que hoy falta y auditoría a ambos caminos. Una migración alinea el histórico aprovechable y descarta —dejando constancia— las 32 marcas sin evidencia detrás.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 / React 18 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic (backend); Vite, Tailwind, TanStack Query v5 (frontend)

**Storage**: MySQL 8 — **una migración de datos**, sin cambios de columnas ni tablas nuevas

**Testing**: pytest (contract / integration) desde la raíz con `backend/.venv`; Vitest en el frontend

**Target Platform**: Docker Compose on-prem detrás de Caddy

**Project Type**: Aplicación web — backend FastAPI + SPA React

**Performance Goals**: la rejilla de cumplimiento debe salir igual o más rápida — al derivar el estado se elimina una consulta (ver [research.md](research.md) R3)

**Constraints**:
- La migración de datos es irreversible en su parte de descarte: debe registrar qué descarta antes de hacerlo.
- El portal del proveedor no puede cambiar de comportamiento observable (R5).
- `CellStatus.VALIDATED` está publicado en contratos y consumido por el portal: el enum **no se toca**.
- No se renombra la columna `documents.verified`; el cambio de término es sólo de interfaz (R8).

**Scale/Scope**: 1 migración, ~8 archivos de backend, ~5 de frontend. 1 endpoint que cambia de semántica, 1 endpoint nuevo (reverso de celda), 1 tabla que queda obsoleta.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Evaluación | Veredicto |
|---|---|---|
| **I. Secure by Default** | Ambos caminos siguen autenticados y con rol comprobado en el servidor. La feature **añade** auditoría donde no la había: la validación de celda pasa a escribir en `audit_log`, que hoy no hace. La única relajación es el permiso de retirar la revisión (R9), decidida explícitamente. | ✅ PASS |
| **II. Multi-Tenant Data Isolation** | No se introducen consultas nuevas fuera del filtro ORM global. La migración corre en `with_admin_scope()` por necesidad, y debe iterar **por organización** sin cruzar datos entre ellas; se cubre con test. | ✅ PASS |
| **III. Test-First for Critical Paths** | Es lógica de autorización y de integridad de evidencia. Los tests de coherencia entre pantallas, de permisos y de la migración se escriben antes de tocar el código. | ✅ PASS |
| **IV. Simplicity and Iteration (YAGNI)** | La feature **elimina** un mecanismo en vez de añadir uno: una tabla deja de ser fuente de verdad, una consulta desaparece, y dos códigos de error se colapsan en uno. No se renombra la columna ni el enum, que sería trabajo sin valor para el usuario. | ✅ PASS |

**Complejidad añadida que requiere justificación**: el único elemento nuevo es el endpoint de reverso a nivel de celda. Se justifica porque FR-006 lo exige y porque hoy la validación de celda es irreversible: unificar sin él dejaría el sistema peor de lo que está.

**Re-evaluación post-diseño (Phase 1)**: sin cambios. El diseño reduce superficie en lugar de ampliarla.

## Project Structure

### Archivos nuevos

```
backend/alembic/versions/00XX_unify_cell_validation_into_documents.py
backend/tests/integration/test_verification_unification.py
backend/tests/integration/test_migration_unify_validation.py
```

### Archivos modificados

```
backend/src/repse/compliance/service.py      # is_type_validated deriva de doc.verified; se elimina la consulta de validaciones
backend/src/repse/compliance/routes.py       # validate → verifica el documento vigente; nuevo unvalidate; exige documento (FR-005)
backend/src/repse/compliance/cell_locks.py   # sólo envío pendiente del portal; la parte de validación se colapsa (R5)
backend/src/repse/compliance/models.py       # ComplianceCellValidation marcada como obsoleta
backend/src/repse/documents/routes.py        # unverify pasa a admin+manager (FR-007)
backend/src/repse/documents/service.py       # auditoría común para ambos caminos
frontend/src/components/documents/VerifiedBadge.tsx          # término único "Validado"
frontend/src/components/documents/DocumentDetailDrawer.tsx   # término único + reverso disponible al gestor
frontend/src/components/documents/DocumentViewerModal.tsx    # validar/quitar validación desde la rejilla
frontend/src/lib/api/index.ts                # tipos y llamadas del reverso
```

### Sin cambios

`CellStatus` y el contrato de la rejilla; el portal del proveedor; el esquema de `documents`.

## Phase 0: Outline & Research

**Completado** → [research.md](research.md)

Nueve puntos: el estado actual de ambos mecanismos (R1), por qué el documento vigente por celda es único y la pregunta abierta queda cerrada (R2), por qué derivar el estado ahorra una consulta (R3), FR-009 sale gratis (R4), los dos códigos de rechazo del borrado se colapsan (R5), la medición real de los datos divergentes (R6), qué hacer con la tabla (R7), el término único de interfaz (R8) y el permiso del reverso (R9).

## Phase 1: Design & Contracts

**Completado** → [data-model.md](data-model.md), [contracts/verification.md](contracts/verification.md), [quickstart.md](quickstart.md)

### Backend

1. **`compliance/service.py`** — `is_type_validated = doc is not None and doc.verified`. Se elimina la consulta de `validation_rows` y el conjunto `validated_cells`. `CellOut.type_validated` conserva su nombre y significado de cara al cliente.

2. **`compliance/routes.py` · validar** — `POST /suppliers/{id}/compliance/validate` deja de insertar en la tabla y pasa a llamar al servicio de verificación sobre el documento vigente de la celda. Si la celda no tiene documento vigente → `422` con `code: no_document_to_validate` (FR-005). Acepta nota opcional (FR-012).

3. **`compliance/routes.py` · reverso** — `POST /suppliers/{id}/compliance/unvalidate`, mismo cuerpo, retira la verificación del documento vigente. Rol admin+manager.

4. **`documents/routes.py`** — `unverify` pasa de `require_role(ADMIN)` a `require_role(ADMIN, MANAGER)` (FR-007).

5. **`compliance/cell_locks.py`** — se queda sólo con la comprobación de `PortalSubmission` pendiente. La parte de `ComplianceCellValidation` desaparece porque ahora es la misma condición que `document_verified`, que 016 ya comprueba (R5).

6. **Auditoría** — ambos caminos pasan por `verify_document` / `unverify_document`, que ya escriben `document.verified` / `document.unverified`. La validación desde la rejilla queda auditada por primera vez (FR-008), sin código nuevo.

### Migración

7. Iterando **por organización**, para cada fila de `compliance_cell_validations`:
   - Si la celda tiene documento vigente no borrado y sin verificar → `verified = True`, `verified_by = validated_by`, `verified_at = validated_at`.
   - Si el documento ya estaba verificado → se respeta su autoría y fecha; no se pisa.
   - Si no hay documento vigente → **se descarta**, registrando en el log de la migración proveedor, tipo, período y fecha de la validación original (32 filas esperadas, R6).
   - La tabla **no se elimina** y queda sin lectores ni escritores (R7).

### Frontend

8. **Término único "Validado"** en `VerifiedBadge`, en el drawer y en el visor (FR-011).
9. **`DocumentViewerModal`** gana el reverso junto al botón de validar, con el estado leído del documento.
10. **Invalidación cruzada**: validar o retirar desde cualquier pantalla invalida las queries de documentos, de cumplimiento del proveedor y del tablero, para que la coherencia sea visible sin recargar (SC-001).

### Orden de ejecución (Principio III)

Test de coherencia entre pantallas → migración con su test → backend → permisos → frontend.

## Phase 2: Task generation approach

`/speckit-tasks` debería producir, en este orden de dependencia:

1. **Base**: derivar el estado en la rejilla y colapsar `cell_locks`. Bloquea el resto porque cambia el significado de "validado" en todo el sistema.
2. **US1 — Una sola marca** (P1): el endpoint de validar pasa a verificar el documento; exigencia de documento; invalidación cruzada en el frontend; tests de coherencia en ambos sentidos.
3. **US2 — Retirar la revisión** (P1): endpoint de reverso, permiso ampliado, botón en ambas pantallas, auditoría del retiro.
4. **US3 — Histórico coherente** (P2): la migración y su test, incluida la constancia de lo descartado.

US3 es independiente de la UI y se valida contra la base de datos. US1 y US2 comparten archivos: conviene secuenciarlas.

## Riesgos y decisiones abiertas

- **Se descartan 32 marcas de validación sin evidencia** (decisión del usuario, R6). Esas celdas volverán a mostrarse como "Faltante" en la rejilla de Prov6. Es visible para el usuario final: conviene avisar antes de desplegar.
- **El gestor podrá retirar la revisión** (R9), cuando hoy es exclusivo del administrador. Única relajación de control de la feature.
- **La tabla obsoleta queda en la base** hasta una migración posterior de retirada. Riesgo bajo (sin lectores ni escritores), pero es deuda declarada.
- **Dependencia con 016**: `cell_locks.py` se creó en esa feature y aquí se reduce. Si 016 no está mergeada, esta feature debe partir de ella.
