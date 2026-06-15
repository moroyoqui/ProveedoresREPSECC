# Tasks: Asignar Proveedor a Usuario

**Input**: Design documents from `/specs/014-user-supplier-assign/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: No se generan tareas de test — no hay rutas nuevas ni lógica de negocio nueva. El backend ya tiene cobertura y los cambios de UI no tienen test automatizado en este proyecto.

**Organization**: Tareas agrupadas por historia de usuario para entrega incremental independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: Historia de usuario a la que pertenece la tarea
- Todos los archivos son existentes — no se crean archivos nuevos

---

## Phase 1: Setup

> Esta feature no requiere setup: no hay nuevas dependencias, migraciones ni archivos de configuración. La fase 2 comienza de inmediato.

---

## Phase 2: Foundational (Prerequisitos bloqueantes)

**Purpose**: Enriquecer `UserOut` con `supplier_name` vía LEFT JOIN — necesario para US2 y US3.

**⚠️ CRITICAL**: Las fases US2 y US3 dependen de que esto esté completo.

- [x] T001 Añadir campo `supplier_name: str | None = None` a la clase `UserOut` en `backend/src/repse/users/schemas.py`
- [x] T002 Actualizar `list_users` en `backend/src/repse/users/routes.py` para hacer LEFT JOIN con `Supplier` y popular `supplier_name` en cada ítem del response
- [x] T003 [P] Añadir campo `supplier_name?: string | null` al tipo `UserItem` en `frontend/src/lib/api/index.ts`

**Checkpoint**: `GET /api/v1/users` devuelve `"supplier_name": "Juan Ruelas"` para usuarios supplier con proveedor, y `null` para los demás.

---

## Phase 3: User Story 1 — Crear usuario supplier con proveedor (Priority: P1) 🎯 MVP

**Goal**: Al crear un nuevo usuario con rol "proveedor", el campo de empresa proveedora aparece y es requerido.

**Independent Test**: Abrir `/settings/users` → "Nuevo usuario" → seleccionar rol "Proveedor" → verificar que aparece selector de empresa proveedora con la lista de proveedores activos → crear el usuario → confirmar que el usuario puede entrar al portal.

**Estado**: Esta historia ya está implementada en `CreateUserDialog` (`frontend/src/pages/users/list.tsx` línea 172). La lógica de backend (`create_user` con `supplier_id`) también existe.

### Implementación para User Story 1

- [x] T004 [US1] Verificar que `CreateUserDialog` en `frontend/src/pages/users/list.tsx` carga `suppliersApi.list({ status: "active" })` cuando `role === "supplier"` y que el campo es requerido para poder enviar el formulario — solo lectura/verificación, sin cambios de código si funciona correctamente

**Checkpoint**: Crear un usuario supplier desde la UI asigna el proveedor correctamente y el usuario puede entrar al portal sin error 409.

---

## Phase 4: User Story 2 — Cambiar/Asignar proveedor a usuario supplier existente (Priority: P2)

**Goal**: Un administrador puede asignar o cambiar el proveedor de un usuario supplier ya creado, desde un diálogo en la tabla de usuarios.

**Independent Test**: Tomar usuario `moroyoqui@gmail.com` (supplier sin proveedor asignado) → abrir "Asignar proveedor" → seleccionar proveedor → guardar → confirmar que la tabla muestra el nombre del proveedor y el usuario puede entrar al portal.

### Implementación para User Story 2

- [x] T005 [US2] Deshabilitar la opción `value="supplier"` en el `<select>` de rol inline de la tabla de usuarios en `frontend/src/pages/users/list.tsx` (línea ~109) añadiendo `disabled` y título explicativo para evitar el error silencioso de API
- [x] T006 [US2] Añadir estado `assignTarget` y botón "Asignar/Cambiar proveedor" en la celda de acciones de la fila (solo cuando `u.role === "supplier"`) en `frontend/src/pages/users/list.tsx`
- [x] T007 [US2] Crear componente `ChangeSupplierDialog` al final de `frontend/src/pages/users/list.tsx`: carga `suppliersApi.list({ status: "active" })`, muestra selector de proveedor inicializado con el actual, llama `usersApi.update(user.id, { supplier_id })` y al éxito invalida `["users"]` y cierra el diálogo
- [x] T008 [US2] Montar `{assignTarget && <ChangeSupplierDialog user={assignTarget} onClose={() => setAssignTarget(null)} />}` al final del JSX del componente `UsersListPage` en `frontend/src/pages/users/list.tsx`

**Checkpoint**: `moroyoqui@gmail.com` puede recibir un proveedor desde la UI y acceder al portal sin error 409.

---

## Phase 5: User Story 3 — Visibilidad del proveedor en el listado (Priority: P3)

**Goal**: La tabla de usuarios muestra el nombre del proveedor asignado (o "Sin asignar") para cada usuario supplier.

**Prerequisito**: Phase 2 (T001-T003) debe estar completa — la columna depende de `supplier_name` en la respuesta de la API.

**Independent Test**: Con varios usuarios supplier asignados a distintos proveedores, verificar que la columna "Proveedor" de la tabla muestra el nombre correcto para cada uno.

### Implementación para User Story 3

- [x] T009 [US3] Añadir `<TH>Proveedor</TH>` en la fila de cabecera de la tabla de usuarios en `frontend/src/pages/users/list.tsx` (después de la columna "Rol")
- [x] T010 [US3] Añadir celda `<TD>` correspondiente en cada fila mostrando `u.supplier_name` cuando `u.role === "supplier"`, el badge "Sin asignar" si es null y rol supplier, o "—" para otros roles, en `frontend/src/pages/users/list.tsx`

**Checkpoint**: La tabla muestra correctamente el proveedor de cada usuario; usuarios con rol distinto a supplier muestran "—".

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T011 [P] Importar icono `Building2` de `lucide-react` en `frontend/src/pages/users/list.tsx` si no está ya importado (usado en el botón "Asignar proveedor" de T006)
- [x] T012 Actualizar `CLAUDE.md` para marcar spec 014 como lista (`[014 ready](specs/014-user-supplier-assign/plan.md)`) en la lista de sibling features

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: Sin dependencias — empezar aquí
- **Phase 3 (US1)**: Solo verificación — puede ejecutarse en paralelo con Phase 2
- **Phase 4 (US2)**: Depende de Phase 2 (necesita `supplier_name` en la respuesta para mostrar nombre actualizado tras asignar)
- **Phase 5 (US3)**: Depende de Phase 2 (necesita `supplier_name` en la API)
- **Phase 6 (Polish)**: Depende de Phase 4 (el import de Building2)

### User Story Dependencies

- **US1 (P1)**: Independiente — ya implementada, solo verificar
- **US2 (P2)**: Depende de Phase 2 completa
- **US3 (P3)**: Depende de Phase 2 completa; US2 y US3 pueden ejecutarse en paralelo una vez Phase 2 esté lista

### Within Each User Story

- T005 → T006 → T007 → T008 (todos en el mismo archivo, secuenciales)
- T009 → T010 (mismo archivo, secuenciales)

### Parallel Opportunities

- T001 y T002 son secuenciales (T002 usa el schema de T001)
- T003 [P] puede ejecutarse en paralelo con T001/T002 (archivo distinto)
- Una vez completa Phase 2: US2 (T005-T008) y US3 (T009-T010) pueden ejecutarse en paralelo
- T011 [P] puede ir con cualquier tarea de frontend

---

## Parallel Example: Phase 2

```
T001 → T002   (schemas.py y routes.py, secuenciales)
T003          (index.ts, en paralelo con T001/T002)
```

## Parallel Example: Phase 4 + Phase 5 (tras completar Phase 2)

```
T005-T008  (list.tsx, US2 — un desarrollador)
T009-T010  (list.tsx, US3 — mismas tareas, ejecutar en secuencia)
```

> Nota: T005-T010 tocan el mismo archivo (`list.tsx`), por lo que en la práctica se ejecutan en una sola sesión de edición.

---

## Implementation Strategy

### MVP (User Story 2 — el bloqueante real)

1. Completar **Phase 2** (T001-T003): añadir `supplier_name` al backend y tipo TS
2. Completar **Phase 4** (T005-T008): diálogo "Asignar proveedor"
3. **VALIDAR**: asignar proveedor a `moroyoqui@gmail.com` desde la UI → login al portal sin error

### Entrega incremental

1. Phase 2 → backend enriquecido ✓
2. Phase 4 → gestión de proveedor en usuarios existentes ✓ (MVP funcional)
3. Phase 5 → visibilidad en tabla ✓
4. Phase 6 → polish ✓

---

## Notes

- [P] = archivos distintos, sin dependencias entre sí
- Todos los cambios son en archivos existentes — delta total estimado: ~60 LOC backend, ~80 LOC frontend
- Sin migraciones de BD
- Sin nuevas rutas de API
- El flujo de creación de usuarios (US1) ya funciona — T004 es solo verificación
