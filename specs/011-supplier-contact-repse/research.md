# Research: Nombre de Contacto y Registro REPSE en Proveedor

**Feature**: 011-supplier-contact-repse  
**Date**: 2026-06-08

---

## Decisión 1: `contact_name` no requiere migración Alembic

**Decision**: No crear migración para `contact_name`; el campo ya existe en la tabla `suppliers` (columna `VARCHAR(255) NULL`).

**Rationale**: El modelo SQLAlchemy `Supplier` ya declara `contact_name: Mapped[str | None] = mapped_column(String(255))`. Los schemas `SupplierIn` y `SupplierPatch` también lo incluyen. La carga de alta de proveedor (`new.tsx`) ya tiene el campo de UI. La tarea se reduce a exponer el campo en:
- `SupplierDetailOut` (schema backend — actualmente ausente)
- `edit.tsx` (formulario de edición — sin estado ni campo de UI)
- `detail.tsx` (ficha de detalle — no se muestra)

**Alternatives considered**: Crear una migración vacía de documentación. Descartado porque no hay cambio de esquema.

---

## Decisión 2: `repse_folio` — VARCHAR(60), texto libre, sin validación de formato

**Decision**: Nuevo campo `repse_folio VARCHAR(60) NULL DEFAULT NULL` en `suppliers`. Sin validación de formato en cliente ni servidor (texto libre).

**Rationale**: El folio REPSE emitido por la STPS no tiene un formato oficial publicado que sea estable. Históricamente los folios han sido numéricos largos o alfanuméricos de hasta ~40 caracteres. VARCHAR(60) cubre cualquier variante conocida con margen. Aplicar un regex de validación hoy podría rechazar folios válidos emitidos bajo formatos anteriores o futuros.

**Alternatives considered**: 
- VARCHAR(40): demasiado ajustado para incluir posibles prefijos o sufijos.
- Validación de regex `^\d{1,20}$`: rechaza folios alfanuméricos de convocatorias STPS anteriores.

---

## Decisión 3: `repse_folio` en el portal — campo de primer nivel en `PortalComplianceGridOut`

**Decision**: Extender `PortalComplianceGridOut` (en `portal/schemas.py`) con `repse_folio: str | None = None`, igual que se hizo con `sector` y `giro` en la feature 010.

**Rationale**: `ComplianceGridOut` contiene un campo `supplier` con un brief limitado (id, legal_name, rfc, supplier_type, status, compliance_percent). Modificar ese brief para añadir `repse_folio` afectaría el schema compartido de cumplimiento. La alternativa más limpia y consistente con la arquitectura actual es añadir `repse_folio` como campo de primer nivel en `PortalComplianceGridOut` y popularlo desde `supplier.repse_folio` en el route del portal.

**Alternatives considered**: 
- Agregar `repse_folio` al `supplier` brief de `ComplianceGridOut`: implica modificar el schema de cumplimiento general para un dato que solo el portal necesita; se descarta.
- Crear un endpoint separado `/portal/profile`: overkill para un solo campo; se descarta.

---

## Decisión 4: `SupplierDetailOut` expone contact_name, contact_email, contact_phone, repse_folio

**Decision**: Añadir los cuatro campos al schema de detalle y al serializador `_serialize_detail` en `routes.py`.

**Rationale**: `SupplierDetailOut` es el contrato que usa la ficha de detalle del admin. Actualmente omite `contact_name`, `contact_email`, `contact_phone` aunque están en el modelo. Se aprovecha esta feature para completar la exposición de todos los datos de contacto más el nuevo folio.

**Alternatives considered**: Añadir solo `contact_name` y `repse_folio` (mínimo requerido por el spec). Descartado porque `contact_phone` y `contact_email` ya están en el modelo y omitirlos en el detalle sería una inconsistencia sin beneficio.

---

## Decisión 5: Migración `0008_add_repse_folio` como única migración de esta feature

**Decision**: Una sola migración Alembic con `revision = "0008_add_repse_folio"` y `down_revision = "0007_add_sectors_giros"`.

**Rationale**: El único cambio de esquema es `ADD COLUMN repse_folio VARCHAR(60) NULL DEFAULT NULL AFTER notes` en la tabla `suppliers`. Agrupar en una sola migración es la práctica estándar del proyecto y mantiene la cadena de revisiones limpia.

---

## Decisión 6: Frontend — `SupplierDetail` extiende con campos de contacto completos

**Decision**: En `frontend/src/lib/api/index.ts`, el tipo `SupplierDetail` (que extiende `SupplierListItem`) incorpora `contact_phone: string | null` y `repse_folio: string | null`. El tipo `SupplierCreate` y `SupplierPatch` también reciben `repse_folio?: string`.

**Rationale**: Mantener los tipos TypeScript alineados con los schemas backend. `SupplierListItem` ya tiene `contact_name` y `contact_email`; `SupplierDetail` añade `contact_phone` y `repse_folio`. `ComplianceGrid` añade `repse_folio?: string | null` para que el portal pueda usarlo desde `data.repse_folio`.

---

## Constitution Check

| Principio | Evaluación |
|-----------|-----------|
| I. Secure by Default | ✅ Sin endpoints nuevos; los existentes ya requieren auth. `repse_folio` no es dato sensible especial. |
| II. Multi-Tenant Isolation | ✅ `suppliers` ya es TenantOwned; el campo nuevo hereda el aislamiento automáticamente. |
| III. Test-First for Critical Paths | ✅ No hay lógica de auth/billing nueva. Sin tests requeridos por spec. |
| IV. Simplicity (YAGNI) | ✅ Cambio mínimo: un campo nuevo + exposición de un campo existente. Sin abstracciones. |
