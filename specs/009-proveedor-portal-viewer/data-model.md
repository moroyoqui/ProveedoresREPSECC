# Data Model: Portal del Proveedor — Visor de Documentación

**Feature**: 009-proveedor-portal-viewer  
**Date**: 2026-05-20 (actualizado con US5 y US6)

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
| `supplier` | Acceso exclusivo al portal de su propio proveedor |

---

## Nueva entidad: `portal_submissions`

Registra los envíos a validación iniciados por el proveedor desde el portal (US6). Una fila representa un paquete de documentos de un tipo específico y período enviado a revisión por contabilidad.

| Columna | Tipo | Nullable | Descripción |
|---|---|---|---|
| `id` | `BIGINT` | NO (PK, autoincrement) | |
| `organization_id` | `BIGINT` | NO | FK → `organizations.id` ON DELETE CASCADE; aislamiento de tenant |
| `supplier_id` | `BIGINT` | NO | FK → `suppliers.id` ON DELETE CASCADE |
| `document_type_id` | `BIGINT` | NO | FK → `document_types.id` ON DELETE RESTRICT |
| `coverage_period_start` | `DATE` | YES | NULL para tipos de documento únicos (`periodicity = 'none'`) |
| `submitted_at` | `DATETIME` | NO | Fecha y hora exacta del envío (UTC); accesible para contabilidad (FR-022) |
| `submitted_by` | `BIGINT` | YES | FK → `users.id` ON DELETE SET NULL; ID del usuario proveedor que presionó "Enviar a validar" |
| `status` | `ENUM('pending','approved','rejected')` | NO | Estado de la solicitud; default `'pending'` |
| `rejection_reason` | `TEXT` | YES | Obligatorio cuando `status = 'rejected'`; visible al proveedor (FR-021) |
| `pre_submission_status` | `ENUM('missing','expired')` | NO | Estado de la celda ANTES del envío; usado para revertir si contabilidad rechaza (FR-021) |
| `created_at` | `DATETIME` | NO | Timestamp de creación del registro |
| `updated_at` | `DATETIME` | NO | Timestamp de última modificación |

**Índices**:
- `idx_portal_submissions_lookup` — `(organization_id, supplier_id, document_type_id, coverage_period_start, status)` — optimiza la lookup del estado de celda en el compliance service.

**Reglas de negocio**:
- Solo puede existir una fila con `status = 'pending'` por combinación `(org_id, supplier_id, doc_type_id, coverage_period_start)`. Validado en la capa de aplicación.
- `rejection_reason` es obligatorio si `status = 'rejected'` (validado en la capa de contabilidad, feature separada).
- Cuando se rechaza una submission: se actualiza `status = 'rejected'` y `rejection_reason`; la celda vuelve a `pre_submission_status`; se habilita carga y re-envío.
- Cuando el proveedor re-envía después de un rechazo: se crea una nueva fila con `status = 'pending'`.

---

## Entidades existentes reutilizadas sin cambios

### `suppliers` (sin cambios)

La entidad proveedor (`Supplier`) ya existe. La feature no modifica su estructura.

### `documents` (sin cambios)

Los documentos de cumplimiento ya existen con toda la información necesaria. El portal los consume para lectura y para upload (reutilizando el servicio existente). No se agregan campos al modelo `Document`.

### `compliance_cell_validations` (sin cambios)

Las validaciones de supervisor siguen manejándose a través de esta tabla. No se mezcla con las submissions del proveedor.

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

## Máquina de estados de celda (perspectiva del proveedor)

```
MISSING/EXPIRED (sin submission pending)
  │
  ├─ [proveedor carga archivo]
  │   └─ La celda sigue en MISSING o EXPIRED hasta el envío
  │
  ├─ [proveedor presiona "Enviar a validar" con al menos 1 archivo]
  │   └─ Se crea portal_submission con status='pending'
  │       └─ SUBMITTED (Pendiente de validación)
  │           │
  │           ├─ [contabilidad aprueba]  → VALIDATED (Vigente)
  │           └─ [contabilidad rechaza con motivo]
  │               └─ Vuelve a MISSING o EXPIRED
  │                   (según pre_submission_status en portal_submission)
  │                   motivo de rechazo visible al proveedor
  │                   re-envío habilitado
  │
PENDING (período actual, sin documento)
  └─ Igual que MISSING para efectos de upload y submit

VALIDATED (Vigente) — no permite nueva carga ni envío
EXPIRING_SOON — no permite nueva carga (celda ya cubierta)
```

### `CellStatus` en el compliance service (sin cambios de esquema)

| Estado | Significado para el proveedor | Carga permitida | Envío permitido |
|---|---|---|---|
| `validated` | Revisado y aprobado por contabilidad | No | No |
| `submitted` | Enviado, pendiente de revisión | No | No (ya enviado) |
| `expiring_soon` | Documento vigente pero próximo a vencer | No | No |
| `expired` | Documento vencido | Sí | Sí (con archivo cargado) |
| `missing` | Período pasado sin documento | Sí | Sí (con archivo cargado) |
| `pending` | Período actual — sin documento aún | Sí | Sí (con archivo cargado) |
| `future` | Período futuro — no aplica | No | No |
| `not_required` | No aplica en este mes | No | No |

El estado `submitted` es determinado por la existencia de una fila activa en `portal_submissions` con `status = 'pending'` para esa celda. El compliance service consultará esta tabla adicionalmente para actualizar los estados de celda afectados.

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

### Al cargar documento desde el portal (US5)

- `supplier_id` del documento = `supplier_id` de la sesión (no configurable por el proveedor).
- `coverage_period_start` ≤ primer día del mes actual (no se permite carga para meses futuros).
- Estado actual de la celda debe ser `missing`, `expired` o `pending`; no se permite carga en `submitted`, `validated`, `expiring_soon`.
- Formato y tamaño validados contra los límites del catálogo de tipos de documento (`DocumentType.max_files`, `DocumentType.allowed_mime_types`, `DocumentType.max_file_size_mb`).
- Si el número de archivos existentes para esa celda ya alcanzó el máximo del catálogo, la carga es bloqueada con mensaje descriptivo.

### Al enviar a validación (US6)

- Debe existir al menos un documento en la celda (`Document` con `supplier_id`, `document_type_id`, `coverage_period_start` correctos y `deleted_at IS NULL`).
- No debe existir una `portal_submission` activa (`status = 'pending'`) para esa celda.
- El estado actual de la celda no debe ser `validated` ni `expiring_soon` (ya cubierta).

---

## Migraciones

### `0005_add_supplier_role_and_user_supplier_link`

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

### `0006_add_portal_submissions`

```sql
CREATE TABLE portal_submissions (
  id              BIGINT         NOT NULL AUTO_INCREMENT,
  organization_id BIGINT         NOT NULL,
  supplier_id     BIGINT         NOT NULL,
  document_type_id BIGINT        NOT NULL,
  coverage_period_start DATE     NULL,
  submitted_at    DATETIME       NOT NULL,
  submitted_by    BIGINT         NULL,
  status          ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  rejection_reason TEXT          NULL,
  pre_submission_status ENUM('missing','expired','pending') NOT NULL,
  created_at      DATETIME       NOT NULL,
  updated_at      DATETIME       NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_ps_org    FOREIGN KEY (organization_id)  REFERENCES organizations(id) ON DELETE CASCADE,
  CONSTRAINT fk_ps_sup    FOREIGN KEY (supplier_id)       REFERENCES suppliers(id)     ON DELETE CASCADE,
  CONSTRAINT fk_ps_doctype FOREIGN KEY (document_type_id) REFERENCES document_types(id) ON DELETE RESTRICT,
  CONSTRAINT fk_ps_user   FOREIGN KEY (submitted_by)      REFERENCES users(id)         ON DELETE SET NULL,
  INDEX idx_portal_submissions_lookup
    (organization_id, supplier_id, document_type_id, coverage_period_start, status)
);
```
