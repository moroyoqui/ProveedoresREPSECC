# Data Model: Portal del Proveedor — Visor de Documentación

**Feature**: 009-proveedor-portal-viewer  
**Date**: 2026-05-19

---

## Cambios en entidades existentes

### `users` (tabla existente — extensión)

Se agrega una columna nullable que vincula a un proveedor específico cuando el rol es `supplier`.

| Columna | Tipo | Nullable | Constraint |
|---|---|---|---|
| `supplier_id` | `BIGINT` | YES | FK → `suppliers.id` ON DELETE SET NULL |

**Regla de negocio**: Si `role = 'supplier'`, entonces `supplier_id` DEBE estar poblado. Si `role ≠ 'supplier'`, `supplier_id` DEBE ser NULL. Esta invariante se aplica en la capa de aplicación (validación de schema en `UserCreate`/`UserPatch`).

### `Role` enum (extensión)

Nuevo valor: `supplier` → `"supplier"`.

Tabla completa después del cambio:

| Valor | Descripción |
|---|---|
| `admin` | Acceso total; gestiona organización, usuarios, catálogos |
| `manager` | Puede cargar y validar documentos; no puede gestionar usuarios |
| `viewer` | Solo lectura sobre la vista administrativa |
| `supplier` | Acceso exclusivo al portal de su propio proveedor (solo lectura) |

---

## Entidades existentes reutilizadas sin cambios

### `suppliers` (sin cambios)

La entidad proveedor (`Supplier`) ya existe. La feature no modifica su estructura. El portal simplemente lee datos de esta tabla a través del servicio de compliance.

### `documents` (sin cambios)

Los documentos de cumplimiento ya existen con toda la información necesaria (estado, fechas de vigencia, versiones). El portal los consume de forma de solo lectura.

### `compliance_cell_validations` (sin cambios)

Las validaciones de celda también se exponen en el portal tal como las ve el administrador.

---

## Payload de sesión (extensión)

`SessionPayload` en `repse/auth/session.py`:

| Campo | Tipo | Cambio |
|---|---|---|
| `user_id` | `int` | Existente |
| `organization_id` | `int` | Existente |
| `role` | `str` | Existente |
| `expires_at` | `datetime` | Existente |
| `supplier_id` | `int \| None` | **NUEVO** — nullable, backward-compatible |

El campo `supplier_id` se serializa en la cookie firmada junto con los demás campos. Si está ausente en una cookie existente (sesiones anteriores a la migración), se lee como `None`.

---

## Validaciones de negocio

### Al crear usuario con `role = "supplier"`

- `supplier_id` es **obligatorio**.
- El `supplier_id` debe pertenecer a la misma `organization_id` del admin que crea el usuario.
- Error `422` si `supplier_id` es NULL con rol supplier.
- Error `404` si el `supplier_id` no existe en la organización.

### Al cambiar rol de un usuario existente

- Si se cambia a `supplier`: `supplier_id` debe estar presente en el body.
- Si se cambia desde `supplier` a otro rol: `supplier_id` se limpia a NULL automáticamente.

---

## Estado de celda desde la perspectiva del proveedor

El portal expone el mismo `CellStatus` que el admin ve:

| Estado | Significado para el proveedor |
|---|---|
| `validated` | Documento revisado y aprobado por el contratante |
| `submitted` | Documento entregado, pendiente de revisión |
| `expired` | Documento vencido durante el período de vigencia |
| `missing` | Período ya pasado sin documento entregado |
| `pending` | Período actual — entrega aún puede realizarse |
| `future` | Período futuro — no aplica aún |
| `not_required` | Este tipo no aplica en este mes |

---

## Migration script: `0005_add_supplier_role_and_user_supplier_link`

```sql
-- Ampliar el ENUM Role con el nuevo valor 'supplier'
ALTER TABLE users MODIFY role ENUM('admin','manager','viewer','supplier') NOT NULL;

-- Agregar FK supplier_id en users
ALTER TABLE users
  ADD COLUMN supplier_id BIGINT NULL DEFAULT NULL,
  ADD CONSTRAINT fk_users_supplier
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL;

CREATE INDEX ix_users_supplier ON users(supplier_id);
```
