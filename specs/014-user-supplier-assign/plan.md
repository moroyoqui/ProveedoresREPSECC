# Implementation Plan: Asignar Proveedor a Usuario

**Branch**: `014-user-supplier-assign` | **Date**: 2026-06-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-user-supplier-assign/spec.md`

## Summary

Exponer en la UI de administración de usuarios la vinculación proveedor-usuario: añadir `supplier_name` al endpoint de listado de usuarios (LEFT JOIN), mostrar una columna "Proveedor" en la tabla, y añadir un diálogo "Cambiar proveedor" para usuarios supplier existentes. El backend ya tiene toda la lógica implementada; los cambios son mínimos y casi exclusivamente de frontend.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / React 18 (frontend)

**Primary Dependencies**: FastAPI + SQLAlchemy 2.x (backend); TanStack Query v5 + Tailwind (frontend)

**Storage**: MySQL 8 — sin migraciones requeridas (`supplier_id` ya existe en `users`)

**Testing**: pytest (backend unit/integration); no hay tests de UI automatizados

**Target Platform**: Web app on-prem con Docker Compose + Caddy

**Project Type**: Web service (back-office admin SPA + portal proveedor)

**Performance Goals**: Sin requisitos especiales — operaciones de gestión de usuarios de baja frecuencia

**Constraints**: Sin migraciones de BD; cambios quirúrgicos sin romper flujos existentes

**Scale/Scope**: Pantalla de usuarios existente (~350 LOC); delta estimado: ~80 LOC backend + ~100 LOC frontend

## Constitution Check

| Principio | Estado | Notas |
|-----------|--------|-------|
| I. Secure by Default | ✅ | `require_role(Role.ADMIN)` ya en todos los endpoints de usuarios; `_validate_supplier_ownership` ya previene cross-tenant |
| II. Multi-Tenant Data Isolation | ✅ | `_validate_supplier_ownership` ya verifica que el proveedor pertenezca a la org del actor |
| III. Test-First para rutas críticas | ✅ | Sin cambios de auth/authz. `supplier_name` es solo lectura — ya cubierto por tests de `list_users` existentes |
| IV. Simplicity / YAGNI | ✅ | Backend: 1 campo en schema + join en list_users. Frontend: 1 columna + 1 diálogo |

## Project Structure

### Documentation (this feature)

```text
specs/014-user-supplier-assign/
├── plan.md              ← este archivo
├── research.md          ← Phase 0
├── data-model.md        ← Phase 1
├── contracts/
│   └── users.md         ← delta del contrato Users
└── tasks.md             ← Phase 2 (generado por /speckit-tasks)
```

### Source Code (archivos modificados)

```text
backend/
└── src/repse/users/
    ├── schemas.py        ← añadir supplier_name a UserOut
    └── routes.py         ← LEFT JOIN en list_users para popular supplier_name

frontend/
└── src/
    ├── lib/api/index.ts  ← añadir supplier_name a UserItem
    └── pages/users/
        └── list.tsx      ← columna Proveedor + diálogo ChangeSupplierDialog
                             + proteger dropdown inline de rol
```

**Structure Decision**: Web application (Option 2). El proyecto ya tiene la estructura `backend/` + `frontend/` separada; se tocan exactamente 4 archivos existentes, sin archivos nuevos.

## Implementation Tasks

### T-001 — Backend: añadir `supplier_name` a `UserOut`

**Archivos**: `backend/src/repse/users/schemas.py`, `backend/src/repse/users/routes.py`

En `schemas.py` añadir a `UserOut`:
```python
supplier_name: str | None = None
```

En `routes.py` cambiar `list_users` para LEFT JOIN con `Supplier`:
```python
from repse.suppliers.models import Supplier

rows = db.execute(
    select(User, Supplier.legal_name.label("supplier_name"))
    .outerjoin(Supplier, User.supplier_id == Supplier.id)
    .order_by(User.email)
).all()
return {
    "items": [
        {**UserOut.model_validate(u).model_dump(), "supplier_name": sname}
        for u, sname in rows
    ],
    "next_cursor": None,
    "has_more": False,
}
```

**Verify**: `GET /api/v1/users` devuelve `"supplier_name": "Juan Ruelas"` para usuarios supplier con proveedor asignado, y `null` para los demás.

---

### T-002 — Frontend: añadir `supplier_name` a `UserItem`

**Archivo**: `frontend/src/lib/api/index.ts`

En el tipo `UserItem` añadir:
```typescript
supplier_name?: string | null;
```

**Verify**: TypeScript compila sin errores (`npm run type-check`).

---

### T-003 — Frontend: columna "Proveedor" en tabla de usuarios

**Archivo**: `frontend/src/pages/users/list.tsx`

1. Añadir `<TH>Proveedor</TH>` entre las columnas "Rol" y "Estado".
2. Añadir celda en cada fila:
```tsx
<TD className="text-sm text-neutral-600">
  {u.role === "supplier"
    ? u.supplier_name ?? <span className="text-status-expired text-xs">Sin asignar</span>
    : "—"}
</TD>
```

**Verify**: La tabla muestra el nombre del proveedor; usuarios sin rol supplier muestran "—".

---

### T-004 — Frontend: proteger dropdown inline de rol contra selección de "supplier"

**Archivo**: `frontend/src/pages/users/list.tsx`

El `<select>` de rol inline llama `updateRole.mutate({ id, role })` sin `supplier_id`, lo que falla si se selecciona "supplier". Deshabilitar la opción:

```tsx
<option value="supplier" disabled>
  {ROLE_LABEL.supplier} (usar "Asignar proveedor")
</option>
```

**Verify**: No se puede seleccionar "supplier" en el dropdown inline; las otras opciones siguen funcionando.

---

### T-005 — Frontend: diálogo "Cambiar/Asignar proveedor" para usuarios supplier existentes

**Archivo**: `frontend/src/pages/users/list.tsx`

Añadir estado y botón en la fila (solo cuando `u.role === "supplier"`):
```tsx
const [assignTarget, setAssignTarget] = useState<UserItem | null>(null);

// en la celda de acciones:
{u.role === "supplier" && (
  <Button size="sm" variant="ghost" onClick={() => setAssignTarget(u)}>
    <Building2 size={14} />
    {u.supplier_id ? "Cambiar proveedor" : "Asignar proveedor"}
  </Button>
)}
```

Añadir al final del archivo el componente `ChangeSupplierDialog`:
- Props: `{ user: UserItem; onClose: () => void }`
- Carga `suppliersApi.list({ status: "active" })` (query key `["suppliers", "active"]`)
- Selector inicializado con `user.supplier_id`
- Llama `usersApi.update(user.id, { supplier_id: selectedId })`
- Invalida `["users"]` al éxito y cierra el diálogo

**Verify**: Un usuario supplier sin proveedor puede ser asignado; uno con proveedor puede cambiarlo; al guardar la tabla se actualiza con el nuevo nombre.

## Complexity Tracking

*Sin violaciones de constitución — no aplica.*
