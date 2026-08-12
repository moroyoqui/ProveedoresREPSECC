---

description: "Task list for 011-supplier-contact-repse implementation"
---

# Tasks: Nombre de Contacto y Registro REPSE en Proveedor

**Input**: Design documents from `/specs/011-supplier-contact-repse/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/suppliers-extension.md ✅

**Tests**: No incluidos (la especificación no los solicita explícitamente).

**Organization**: Tareas agrupadas por historia de usuario. US1 (contact_name) y US2 (repse_folio) son ambas P1 y comparten algunos archivos backend — se ejecutan secuencialmente en ese archivo, en paralelo en archivos distintos.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: Historia de usuario a la que pertenece (US1–US2)

---

## Phase 1: Foundational — Migración y modelo (BLOQUEANTE para US2)

**Purpose**: Añadir la columna `repse_folio` a la tabla `suppliers` en BD. Bloqueante para US2; US1 puede avanzar en paralelo (no requiere migración).

- [X] T001 Añadir campo `repse_folio: Mapped[str | None] = mapped_column(String(60), nullable=True)` al modelo `Supplier` en `backend/src/repse/suppliers/models.py`
- [X] T002 Crear migración Alembic `0008_add_repse_folio.py` en `backend/alembic/versions/` con `revision="0008_add_repse_folio"`, `down_revision="0007_add_sectors_giros"`: `ALTER TABLE suppliers ADD COLUMN repse_folio VARCHAR(60) NULL DEFAULT NULL AFTER notes;`
- [X] T003 Aplicar migración en el contenedor: `docker compose exec app alembic upgrade head` desde `ops/`

**Checkpoint**: La columna `repse_folio` existe en la BD; el modelo Python la mapea. US1 y US2 pueden avanzar.

---

## Phase 2: User Story 1 — Exponer nombre de contacto del proveedor (Priority: P1) 🎯 MVP

**Goal**: El campo `contact_name` (ya almacenado en BD) aparece en la ficha de detalle del proveedor y en el formulario de edición.

**Independent Test**: Abrir la edición de un proveedor existente que tenga `contact_name` en BD, verificar que el campo aparece pre-poblado, editarlo, guardar y confirmar que el detalle del proveedor muestra el nombre actualizado.

### Backend — US1

- [X] T004 [US1] Añadir `contact_name: str | None`, `contact_email: EmailStr | None`, `contact_phone: str | None` a `SupplierDetailOut` en `backend/src/repse/suppliers/schemas.py`
- [X] T005 [US1] Mapear los tres campos de contacto en `_serialize_detail(...)` en `backend/src/repse/suppliers/routes.py`: `contact_name=supplier.contact_name, contact_email=supplier.contact_email, contact_phone=supplier.contact_phone`

### Frontend — US1

- [X] T006 [P] [US1] Añadir `contact_phone: string | null` a `SupplierDetail` (tipo en `frontend/src/lib/api/index.ts`) para recibir el teléfono desde el detail endpoint
- [X] T007 [P] [US1] Añadir estado `contactName` (inicializado desde `supplierQ.data.contact_name`) + `<FormField name="contact_name" label="Nombre de contacto" .../>` al formulario de edición en `frontend/src/pages/suppliers/edit.tsx`; incluir `contact_name: contactName || undefined` en `baseFields()`
- [X] T008 [US1] Mostrar bloque de contacto (nombre · correo · teléfono) en la ficha de detalle del proveedor en `frontend/src/pages/suppliers/detail.tsx` debajo de sector/giro

**Checkpoint**: US1 completa — el nombre de contacto se edita y se visualiza correctamente.

---

## Phase 3: User Story 2 — Registrar y visualizar folio REPSE (Priority: P1)

**Goal**: El campo `repse_folio` (nuevo) se puede capturar en alta y edición de proveedor, aparece en la ficha de detalle y en el portal del proveedor en modo solo lectura.

**Independent Test**: Crear un proveedor nuevo con folio REPSE, verificar que aparece en la ficha de detalle; abrir el portal con un usuario `supplier` vinculado y comprobar que el folio aparece en solo lectura.

### Backend — US2

- [X] T009 [US2] Añadir `repse_folio: str | None = Field(None, max_length=60)` a `SupplierIn` y `SupplierPatch`; añadir `repse_folio: str | None = None` a `SupplierDetailOut` en `backend/src/repse/suppliers/schemas.py`
- [X] T010 [US2] Mapear `repse_folio=supplier.repse_folio` en `_serialize_detail(...)` en `backend/src/repse/suppliers/routes.py`
- [X] T011 [P] [US2] Añadir `repse_folio: str | None = None` a `PortalComplianceGridOut` en `backend/src/repse/portal/schemas.py`
- [X] T012 [P] [US2] En `portal_compliance(...)` de `backend/src/repse/portal/routes.py`, leer `repse_folio = supplier.repse_folio if supplier is not None else None` y pasarlo al constructor `PortalComplianceGridOut(..., repse_folio=repse_folio)`

### Frontend — US2

- [X] T013 [P] [US2] Añadir `repse_folio?: string` a `SupplierCreate` y `SupplierPatch`; añadir `repse_folio: string | null` a `SupplierDetail`; añadir `repse_folio?: string | null` a `ComplianceGrid` en `frontend/src/lib/api/index.ts`
- [X] T014 [P] [US2] Añadir `repse_folio: z.string().max(60).optional()` al schema Zod + `<FormField name="repse_folio" label="Folio REPSE" placeholder="REPSE-2024-00001234" />` + incluir `repse_folio: parsed.data.repse_folio || undefined` en el payload de `frontend/src/pages/suppliers/new.tsx`
- [X] T015 [P] [US2] Añadir estado `repseFollio` (inicializado desde `supplierQ.data.repse_folio`) + `<FormField name="repse_folio" label="Folio REPSE" .../>` + incluir en `baseFields()` en `frontend/src/pages/suppliers/edit.tsx`
- [X] T016 [US2] Mostrar `repse_folio` en la ficha de detalle del proveedor (en bloque `font-mono`) en `frontend/src/pages/suppliers/detail.tsx`
- [X] T017 [US2] Mostrar `repse_folio` en modo solo lectura en el portal del proveedor en `frontend/src/pages/portal/index.tsx`

**Checkpoint**: US2 completa — el folio REPSE se captura en alta/edición, se muestra en el detalle y en el portal.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Verificaciones de integridad cruzada.

- [X] T018 [P] Verificar que un proveedor existente con `contact_name` en BD pre-puebla el campo correctamente al abrir el formulario de edición en `frontend/src/pages/suppliers/edit.tsx`
- [X] T019 [P] Verificar que borrar el folio REPSE en edición (campo vacío → null) se persiste correctamente y el detalle muestra el campo como ausente

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Foundational — migración)
    ↓ (desbloquea US2; US1 puede avanzar en paralelo)
US1 (Phase 2) ─┐ (en paralelo si hay capacidad)
US2 (Phase 3) ─┘ (requiere Phase 1 completa para backend)
    ↓
Polish (Phase 4)
```

### Conflictos de archivos entre US1 y US2

US1 y US2 modifican los mismos archivos backend (`schemas.py`, `routes.py`) y frontend (`edit.tsx`, `detail.tsx`). Por ello, aunque son P1, deben ejecutarse **secuencialmente en esos archivos**:

- `schemas.py`: T004 (US1) → T009 (US2) — en el mismo archivo, secuencial
- `routes.py`: T005 (US1) → T010 (US2) — secuencial
- `edit.tsx`: T007 (US1) → T015 (US2) — secuencial
- `detail.tsx`: T008 (US1) → T016 (US2) — secuencial

Los tasks marcados [P] dentro de cada fase son paralelos entre sí porque afectan archivos distintos.

### Within Each User Story

- Backend (schemas → routes) antes que frontend (tipos → UI)
- El contrato API definido en `contracts/suppliers-extension.md` permite avanzar frontend e incluso en paralelo si se simula la respuesta

### Parallel Opportunities

- T001 y T004 (model + US1 schemas) pueden avanzar en paralelo (archivos distintos)
- T006 y T007 (frontend US1) en paralelo entre sí
- T011 y T012 (portal schemas + api types) en paralelo
- T013, T014 (new.tsx + edit.tsx US2) en paralelo
- T018 y T019 (polish) en paralelo

---

## Parallel Example: User Story 2

```bash
# Backend — secuencial por dependencias en mismo archivo:
T009: schemas.py (SupplierIn, SupplierPatch, SupplierDetailOut)
T010: routes.py (_serialize_detail)

# Portal backend — paralelo entre sí:
T011: portal/schemas.py
T012: portal/routes.py

# Frontend — en paralelo entre sí:
T013: lib/api/index.ts
T014: pages/suppliers/new.tsx
T015: pages/suppliers/edit.tsx
# Luego:
T016: pages/suppliers/detail.tsx  (depende de T013)
T017: pages/portal/index.tsx      (depende de T013)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Phase 1 (migración aplicada)
2. Completar Phase 2 (US1 — contact_name en detalle y edición)
3. **VALIDAR**: Abrir edición de un proveedor existente, verificar campo pre-poblado, guardar y ver en detalle
4. Continuar con US2 (repse_folio)

### Incremental Delivery

1. Phase 1 → BD preparada
2. US1 → `contact_name` visible en edición y detalle
3. US2 → `repse_folio` en toda la pila (alta, edición, detalle, portal)
4. Polish → verificaciones de edge cases

---

## Notes

- `contact_name` ya existe en el modelo y en los schemas de escritura; **solo falta** en `SupplierDetailOut` y en el formulario de edición
- `repse_folio` es campo nuevo en toda la pila; requiere migración (T002) antes de usarse
- Ambos campos son **nullable / opcionales**; el guardado sin ellos debe funcionar correctamente
- El bloque `font-mono` para `repse_folio` en el detalle facilita la legibilidad de identificadores alfanuméricos
- La validación `max_length=60` en Pydantic actúa como guard; el modelo BD usa `VARCHAR(60)` como techo
