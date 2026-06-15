# Data Model: Asignar Proveedor a Usuario

## Sin cambios de esquema de BD

La columna `users.supplier_id` (FK → `suppliers.id`, nullable, ON DELETE SET NULL) ya existe. No se requieren migraciones.

## Cambios en capa de serialización

### UserOut (backend/src/repse/users/schemas.py)

Campo nuevo a añadir:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `supplier_name` | `str \| None` | Nombre legal del proveedor vinculado; NULL si el usuario no tiene proveedor asignado |

Obtenido mediante LEFT JOIN en `list_users`: `db.execute(select(User, Supplier.legal_name).outerjoin(Supplier, User.supplier_id == Supplier.id))`.

### UserItem (frontend/src/lib/api/index.ts)

Campo nuevo a añadir al tipo TypeScript:

```typescript
supplier_name?: string | null;
```

## Flujo de asignación (existente, sin cambios)

```
POST /users          body: { role: "supplier", supplier_id: N, ... }
PATCH /users/{id}    body: { supplier_id: N }   (usuario ya es supplier)
PATCH /users/{id}    body: { role: "supplier", supplier_id: N }  (cambio de rol + asignación)
```

Validaciones ya implementadas en `_validate_supplier_ownership`:
- `supplier_id` no puede ser NULL para rol supplier
- El proveedor debe pertenecer a la misma organización

## Estado de vinculación

| Estado | `role` | `supplier_id` | Puede usar portal |
|--------|--------|---------------|-------------------|
| Normal | supplier | ≠ NULL | Sí |
| Sin asignar | supplier | NULL | No (409) |
| Otro rol | admin/manager/viewer | NULL | No aplica |
