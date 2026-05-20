# Implementation Plan: Portal del Proveedor — Visor de Documentación

**Branch**: `009-proveedor-portal-viewer` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-proveedor-portal-viewer/spec.md`

---

## Summary

Se añade un nuevo rol `supplier` al sistema, se vincula cada usuario proveedor a su empresa mediante un FK en `users.supplier_id`, y se expone un portal de solo lectura (`GET /api/v1/portal/compliance`) que reutiliza el servicio de cumplimiento existente. En el frontend, los usuarios con rol `supplier` son redirigidos al portal y ven una navegación mínima. Los administradores pueden crear usuarios proveedor y asociarlos a su empresa en el mismo flujo de creación de usuarios.

---

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript / React 18 (frontend)

**Primary Dependencies**: FastAPI · SQLAlchemy 2.x · itsdangerous (sesión) · TanStack Query v5 · React Router v6 · Tailwind CSS

**Storage**: MySQL 8 — extensión de la tabla `users` (columna `supplier_id`) + modificación del ENUM `role`

**Testing**: pytest (backend) · Vitest (frontend, cuando exista cobertura)

**Target Platform**: Aplicación web on-prem; mismo entorno Docker Compose existente

**Project Type**: Web service (FastAPI) + SPA (React/Vite)

**Performance Goals**: El portal debe cargar en < 5 s (incluye login redirect); sin nuevos objetivos de throughput

**Constraints**: Portal de solo lectura en v1; el `supplier_id` nunca sale de la sesión firmada del servidor

**Scale/Scope**: Hasta ~100 usuarios proveedor por organización; sin paginación especial requerida

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principio | Estado | Notas |
|---|---|---|
| I. Secure by Default | PASS | Portal endpoint requiere auth + `require_role("supplier")`; `supplier_id` se impone desde la sesión firmada, nunca desde el request |
| II. Multi-Tenant Data Isolation | PASS | `organization_id` de la sesión sigue siendo el scope primario; `supplier_id` scope secundario. **Test negativo requerido**: supplier A no puede ver datos de supplier B |
| III. Test-First Critical Paths | PASS | Requiere test de auth gate (401/403) y test de aislamiento tenant/supplier antes del merge |
| IV. Simplicity (YAGNI) | PASS | Reutiliza `get_annual_compliance()` sin modificaciones; FK nullable en lugar de tabla de enlace; portal sin escritura |

---

## Project Structure

### Documentation (this feature)

```text
specs/009-proveedor-portal-viewer/
├── plan.md              <- Este archivo
├── research.md          <- Decisiones técnicas
├── data-model.md        <- Cambios en entidades y migración
├── contracts/
│   └── portal-compliance.md
└── tasks.md             <- Generado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 0005_add_supplier_role_and_user_supplier_link.py   <- NUEVO
├── src/repse/
│   ├── users/
│   │   ├── models.py          <- Role enum + supplier_id FK
│   │   ├── schemas.py         <- UserCreate/UserOut + supplier_id
│   │   └── routes.py          <- Validación supplier_id al crear/patchear
│   ├── auth/
│   │   ├── session.py         <- SessionPayload + supplier_id (nullable)
│   │   ├── dependencies.py    <- CurrentUser + supplier_id
│   │   └── routes.py          <- /me expone supplier_id; login incluye supplier_id en payload
│   └── portal/
│       ├── __init__.py        <- NUEVO
│       └── routes.py          <- NUEVO — GET /portal/compliance
│
frontend/src/
├── lib/
│   ├── auth.tsx               <- Role type + supplierId en AuthUser
│   └── api/
│       ├── index.ts           <- Role type + UserItem.supplier_id + UserCreate.supplier_id
│       └── portal.ts          <- NUEVO — portalApi.getCompliance()
├── app/
│   └── router.tsx             <- /portal route + redirect por rol supplier
├── components/layout/
│   └── AppShell.tsx           <- Nav mínima para rol supplier
└── pages/
    ├── portal/
    │   └── index.tsx          <- NUEVO — PortalPage
    └── users/
        └── list.tsx           <- supplier selector en CreateUserDialog
```

---

## Implementation Steps

### US1 — Backend: Rol `supplier` + vínculo usuario-proveedor

#### T01 — Migration `0005`
- Archivo: `backend/alembic/versions/0005_add_supplier_role_and_user_supplier_link.py`
- **upgrade**: `ALTER TABLE users MODIFY role ENUM('admin','manager','viewer','supplier') NOT NULL; ALTER TABLE users ADD COLUMN supplier_id BIGINT NULL; ADD CONSTRAINT fk_users_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL; CREATE INDEX ix_users_supplier ON users(supplier_id)`
- **downgrade**: eliminar índice, FK y columna; revertir ENUM.

#### T02 — `backend/src/repse/users/models.py`
- Agregar `SUPPLIER = "supplier"` al `Role` StrEnum.
- Agregar campo `supplier_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)`.

#### T03 — `backend/src/repse/users/schemas.py`
- `UserOut`: agregar `supplier_id: int | None = None`.
- `UserCreate`: agregar `supplier_id: int | None = None` con validador `@model_validator` que exige `supplier_id` si `role == Role.SUPPLIER`.
- `UserPatch`: agregar `supplier_id: int | None = None`.

#### T04 — `backend/src/repse/users/routes.py`
- `create_user`: si `body.role == Role.SUPPLIER`, verificar que `body.supplier_id` existe y pertenece a `user.organization_id`; asignar `new.supplier_id`.
- `update_user`: si cambia a `supplier`, validar `body.supplier_id`; si cambia desde `supplier` a otro rol, setear `row.supplier_id = None`.

---

### US2 — Backend: Sesión con `supplier_id`

#### T05 — `backend/src/repse/auth/session.py`
- `SessionPayload`: agregar `supplier_id: int | None = None`.
- `issue()`: incluir `"supplier_id": payload.supplier_id` en el dict.
- `read()`: leer con `.get("supplier_id")` (backward-compatible).

#### T06 — `backend/src/repse/auth/dependencies.py`
- `CurrentUser`: agregar `supplier_id: int | None = None`.
- `current_user()`: propagar `payload.supplier_id`.

#### T07 — `backend/src/repse/auth/routes.py`
- `login_local` y `callback` (OIDC): incluir `supplier_id=user.supplier_id` al construir `SessionPayload`.
- `/me`: incluir `"supplier_id": user.supplier_id` en la respuesta.

---

### US3 — Backend: Portal endpoint

#### T08 — `backend/src/repse/portal/__init__.py`
- Archivo vacío de paquete.

#### T09 — `backend/src/repse/portal/routes.py`
- `GET /portal/compliance?year=N`: requiere `require_role(Role.SUPPLIER.value)`; obtiene `supplier_id` de `user.supplier_id`; llama a `compliance.service.get_annual_compliance()`; devuelve `ComplianceGridOut`.
- Devuelve `409 Conflict` con `code="supplier_not_linked"` si `user.supplier_id is None`.

#### T10 — `backend/src/repse/main.py`
- Importar y registrar el router del portal con prefijo `/api/v1`.

---

### US4 — Backend: Tests críticos

#### T11 — Tests de autenticación y autorización
- Sin cookie → 401.
- Rol admin/manager/viewer → 403.
- Rol supplier sin `supplier_id` en sesión → 409.
- Rol supplier con `supplier_id` válido → 200 + datos correctos.

#### T12 — Test de aislamiento (Constitution II — obligatorio)
- Supplier A no puede ver datos de supplier B en la misma organización.
- Supplier de organización X no puede ver datos de organización Y.

---

### US5 — Frontend: Tipos para rol `supplier`

#### T13 — `frontend/src/lib/auth.tsx`
- Agregar `"supplier"` a `Role` type.
- Agregar `supplierId?: number | null` a `AuthUser`.

#### T14 — `frontend/src/lib/api/index.ts`
- Agregar `"supplier"` al type `Role`.
- Agregar `supplier_id?: number | null` a `UserItem` y `UserCreate`.

---

### US6 — Frontend: Enrutamiento por rol

#### T15 — `frontend/src/app/router.tsx`
- Importar `PortalPage`.
- Agregar `<Route path="portal" element={<PortalPage />} />`.
- Cambiar el redirect root para que `supplier` → `/portal`, resto → `/suppliers`.
- En `setUser` dentro de `RequireAuth`: mapear `me.supplier_id` a `supplierId`.

#### T16 — `frontend/src/components/layout/AppShell.tsx`
- Para `role === "supplier"`: mostrar solo ítem "Mi documentación" (`/portal`, icono `FileStack`) y logout.
- El nombre de organización y RFC se siguen mostrando.

---

### US7 — Frontend: Portal page

#### T17 — `frontend/src/lib/api/portal.ts` (NUEVO)
- `portalApi.getCompliance(year?: number): Promise<ComplianceGridOut>` → `GET /api/v1/portal/compliance[?year=N]`.
- Reutiliza `apiFetch` del módulo `api` existente.

#### T18 — `frontend/src/pages/portal/index.tsx` (NUEVO)
- Cabecera: nombre del proveedor, RFC, porcentaje de cumplimiento y nombre del tipo de proveedor.
- Selector de año (2020–actual).
- Sección de alertas: filtra celdas del mes actual con status `missing`, `expired`, `pending`; las muestra agrupadas con días restantes si hay fecha de vencimiento.
- Lista de `monthly_requirements`: usa `ComplianceCell` existente para los badges.
- Sección `one_time_requirements` si la lista no está vacía.
- Sin botones de carga ni validación (portal read-only).

---

### US8 — Frontend: Crear usuario proveedor

#### T19 — `frontend/src/pages/users/list.tsx`
- Agregar `supplier: "Proveedor"` a `ROLE_LABEL`.
- Agregar `<option value="supplier">` en los `<select>` de rol (tanto en la lista como en el diálogo de creación).
- En `CreateUserDialog`:
  - Cuando `role === "supplier"`, mostrar un `<select>` con los proveedores activos de la organización (query a `suppliersApi.list()`).
  - El campo es requerido; si no hay selección y rol = supplier, el botón "Crear" queda deshabilitado.
  - Incluir `supplier_id` en el body del `UserCreate` al invocar `usersApi.create()`.

---

## Notes

- Las cookies de sesión existentes (sin `supplier_id`) seguirán siendo válidas; se leerán con `supplier_id = None` — backward-compatible.
- La migración 0005 usa `MODIFY role ENUM(...)` en MySQL; Alembic no soporta nativamente el tipo nativo MySQL ENUM, pero el proyecto ya usa `native_enum=False` + `values_callable` — la migración debe usar `sa.Enum(..., native_enum=False)` o `text()` para el ALTER.
- El componente `ComplianceCell` existente no necesita modificaciones para el portal.
- No se crean endpoints `POST`/`PATCH`/`DELETE` en el módulo `portal/`.
