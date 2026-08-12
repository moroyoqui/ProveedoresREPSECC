# Tasks: Mejoras UX tabla de usuarios (015)

**Input**: Design documents from `specs/015-users-list-ux/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓

**Tests**: No incluidos — cambios de presentación pura sin lógica de auth/billing; la verificación se hace manualmente en el navegador.

**Organization**: Tareas agrupadas por historia de usuario para implementación y verificación independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin bloqueos)
- **[Story]**: historia de usuario a la que pertenece (US1, US2, US3)

---

## Phase 1: Setup — Componente compartido `IconButton`

**Purpose**: Crear el primitivo `IconButton` con tooltip que US2 necesita y que podría reutilizarse en futuras features.

- [x] T001 Crear componente `frontend/src/components/ui/IconButton.tsx` con props: `icon`, `label` (aria-label + tooltip), `onClick`, `disabled`, `variant` ("ghost" | "secondary"); tooltip via Tailwind `group` + `absolute` sin dependencia nueva
- [x] T002 Re-exportar `IconButton` desde `frontend/src/components/ui/index.ts`

**Checkpoint**: `IconButton` disponible para importar desde `@/components/ui`.

---

## Phase 2: Foundational — Sin bloqueos adicionales

Esta feature no tiene infraestructura de backend ni de routing que preparar. El trabajo empieza directamente en las historias de usuario.

---

## Phase 3: User Story 1 — Nombre clicable abre panel de detalle (Priority: P1) 🎯 MVP

**Goal**: El administrador hace clic en el nombre de un usuario y ve un modal de solo lectura con todos sus datos.

**Independent Test**: Con la tabla cargada, hacer clic en el nombre de cualquier usuario debe abrir el modal con: nombre, correo, rol (en español), estado (badge), proveedor (si aplica).

### Implementación US1

- [x] T003 [US1] En `frontend/src/pages/users/list.tsx`: añadir estado `detailTarget: UserItem | null` y agregar el componente `UserDetailDrawer` al árbol de renderizado (al final del return, junto a los demás diálogos)
- [x] T004 [US1] En `frontend/src/pages/users/list.tsx`: convertir la celda del nombre (`<TD>`) en un `<button>` o `<span>` con `cursor-pointer underline text-brand-700` que dispare `setDetailTarget(u)` al hacer clic
- [x] T005 [US1] Definir componente interno `UserDetailDrawer` en `frontend/src/pages/users/list.tsx` (debajo de `ChangeSupplierDialog`): modal centrado con `fixed inset-0 z-40` reutilizando `Card / CardHeader / CardTitle / CardBody`; muestra: nombre, correo, rol (`ROLE_LABEL`), estado (badge), proveedor (`supplier_name` si rol=supplier, "—" si no); botón "Cerrar" que llama `onClose`

**Checkpoint**: Clic en nombre abre modal; Esc o botón Cerrar lo cierra; datos del usuario correctos.

---

## Phase 4: User Story 2 — Íconos con tooltip (Priority: P2)

**Goal**: Los botones de acción (Contraseña, Deshabilitar/Habilitar, Asignar proveedor) se reemplazan por íconos compactos; al hacer hover aparece el tooltip con la acción.

**Independent Test**: Con la tabla cargada, todos los íconos de acción son visibles y sus tooltips se muestran en hover; hacer clic ejecuta exactamente la misma acción que antes.

**Prerequisite**: T001–T002 (IconButton disponible).

### Implementación US2

- [x] T006 [US2] En `frontend/src/pages/users/list.tsx`: importar `IconButton` desde `@/components/ui`; reemplazar los tres `<Button size="sm" variant="ghost/secondary">` de la columna de acciones por `<IconButton>` equivalentes:
  - Contraseña: `icon=<KeyRound size={16}>`, `label="Cambiar contraseña"`, `variant="ghost"`, `onClick={() => setResetTarget(u)}`
  - Deshabilitar (activo): `icon=<ShieldOff size={16}>`, `label="Deshabilitar"`, `variant="secondary"`, `disabled={u.id === currentUser?.id || disable.isPending}`, `onClick={() => disable.mutate(u.id)}`
  - Habilitar (deshabilitado): `icon=<UserCheck size={16}>`, `label="Habilitar"`, `variant="secondary"`, `disabled={enable.isPending}`, `onClick={() => enable.mutate(u.id)}`
  - Asignar proveedor (solo si rol=supplier): `icon=<Building2 size={16}>`, `label="Asignar proveedor"`, `variant="ghost"`, `onClick={() => setAssignTarget(u)}`
- [x] T007 [US2] Verificar que el `import` de `Button` en `list.tsx` se mantiene (aún lo usa `CreateUserDialog`); eliminar del import solo los props que ya no se usen en la tabla (no tocar los diálogos)

**Checkpoint**: Columna de acciones muestra solo íconos; tooltip visible en hover; todas las acciones siguen funcionando.

---

## Phase 5: User Story 3 — Tabla responsiva sin columna "Último acceso" (Priority: P3)

**Goal**: Eliminar la columna "Último acceso" de la tabla; la tabla ya tiene `overflow-x-auto` (corregido en esta misma rama).

**Independent Test**: La columna "Último acceso" no aparece en ningún estado; en viewport ≥ 900 px todas las columnas caben sin scroll horizontal con íconos compactos.

### Implementación US3

- [x] T008 [US3] En `frontend/src/pages/users/list.tsx`: eliminar el `<TH>Último acceso</TH>` de la fila de encabezados
- [x] T009 [US3] En `frontend/src/pages/users/list.tsx`: eliminar la `<TD>` que renderiza `u.last_login_at` de cada fila del cuerpo
- [x] T010 [US3] Verificar que el campo `last_login_at` en el import del tipo `UserItem` permanece (es parte del tipo de la API, no debe eliminarse del tipo, solo del renderizado)

**Checkpoint**: Tabla renderiza 6 columnas (Nombre, Correo, Rol, Proveedor, Estado, Acciones); no aparece "Último acceso".

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T011 [P] Verificar accesibilidad básica: `IconButton` usa `aria-label={label}`; el nombre clicable tiene `role="button"` o es un `<button>` real con `type="button"` para navegación por teclado
- [x] T012 [P] Revisar que `last_login_at` se eliminó del renderizado pero **no** del tipo `UserItem` en `frontend/src/lib/api/index.ts` (el campo lo sigue devolviendo la API)
- [x] T013 Smoke test manual en `http://localhost:9080/users`: (a) tabla sin columna "Último acceso"; (b) nombre clicable abre modal; (c) íconos con tooltips correctos; (d) acciones siguen funcionando; (e) botón "Nuevo usuario" y diálogos existentes sin regresiones

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Sin dependencias — empieza inmediatamente
- **Phase 3 (US1)**: Sin dependencia de Phase 1; puede empezar en paralelo con Phase 1
- **Phase 4 (US2)**: Depende de Phase 1 (necesita `IconButton`)
- **Phase 5 (US3)**: Sin dependencias — puede empezar en cualquier momento
- **Phase 6 (Polish)**: Depende de todas las fases anteriores

### User Story Dependencies

- **US1 (P1)**: Independiente — solo modifica `list.tsx`
- **US2 (P2)**: Depende de T001–T002 (IconButton); independiente de US1
- **US3 (P3)**: Completamente independiente

### Parallel Opportunities

- T001 y T003–T004 pueden ejecutarse en paralelo (archivos distintos)
- T008–T009 pueden ejecutarse en paralelo con cualquier otra historia
- T011–T012 pueden ejecutarse en paralelo en la fase de polish

---

## Parallel Example

```
# Inicio en paralelo:
T001 — crear IconButton.tsx
T003 — añadir estado detailTarget en list.tsx

# Después de T001:
T002 — re-exportar IconButton
T006 — reemplazar botones (después de T002)

# Después de T003:
T004 — nombre clicable
T005 — UserDetailDrawer

# Independiente en cualquier momento:
T008 — eliminar TH "Último acceso"
T009 — eliminar TD last_login_at
```

---

## Implementation Strategy

### MVP (US1 solamente)

1. Completar Phase 1: T001–T002
2. Completar Phase 3: T003–T005
3. **Validar**: clic en nombre abre modal con datos correctos
4. Continuar con US2 y US3

### Entrega incremental

1. US3 primero (más simple, sin dependencias) → tabla sin columna
2. US1 → panel de detalle
3. US2 → íconos con tooltip (requiere IconButton listo)
4. Polish → smoke test final

---

## Notes

- [P] = archivos distintos, sin bloqueos entre sí
- No se modifican schemas del backend ni queries de API
- El tipo `UserItem` en `index.ts` NO se toca — solo el renderizado en `list.tsx`
- `ChangeSupplierDialog` sigue con título "Asignar proveedor" (ya corregido antes de esta feature)
- Verificar regresiones en `CreateUserDialog`, `ResetPasswordDialog` y `ChangeSupplierDialog` en T013
