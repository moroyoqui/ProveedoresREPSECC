# Implementation Plan: Carga Múltiple y Visualizador de Documentos

**Branch**: `001-repse-compliance-tracker` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-multi-upload-doc-viewer/spec.md`

## Summary

Extiende la cuadrícula de cumplimiento REPSE con tres capacidades: carga múltiple de archivos (US1), visualizador en línea sin descarga automática (US2/US3), contador de archivos en la esfera (US3), carga adicional desde el visualizador (New US3), verificación de archivos individuales desde el visualizador (US5), y validación explícita del tipo de documento como unidad (US6). US1–US5 están completamente implementadas (Phase 2–N en tasks.md). La Phase 8 (US6) es la única pendiente.

El cambio central de US6: el estado `VALIDATED` de una celda pasa a ser una acción explícita a nivel de **tipo de documento** (persiste en `compliance_cell_validations`), separada de la verificación de archivos individuales (`documents.verified`). La celda ya no hereda `VALIDATED` de `doc.verified`; un supervisor debe hacer clic en "Marcar como Validado" desde el visualizador para que la celda muestre ese estado.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)

**Primary Dependencies**: FastAPI 0.110+, SQLAlchemy 2.x, Alembic (backend); React 18, Vite 5, Tailwind CSS 3, TanStack Query v5, Lucide React (frontend)

**Storage**: MySQL 8 — nueva tabla `compliance_cell_validations` (ver `data-model.md`)

**Testing**: No se requieren tests automatizados para esta entrega (igual que el resto del feature)

**Target Platform**: On-premise Docker Compose con Caddy reverse proxy

**Project Type**: Web service (backend REST API) + SPA (frontend React)

**Performance Goals**: La query adicional sobre `compliance_cell_validations` debe ejecutarse en la misma llamada que el grid anual; latencia total < 500 ms en red local

**Constraints**: Multi-tenant estricto — cada query filtra por `organization_id`; el endpoint de validación requiere rol ADMIN o MANAGER

**Scale/Scope**: ~50–500 proveedores por organización, ~12 celdas/proveedor/año; la tabla `compliance_cell_validations` tendrá < 100k filas

## Constitution Check

### I. Secure by Default ✓
- Endpoint `POST /suppliers/{id}/compliance/validate` requiere autenticación (`current_user`) y rol ADMIN/MANAGER (`require_role`).
- El frontend oculta el botón "Marcar como Validado" para usuarios con rol visor, pero la seguridad real la aplica el backend.
- No se almacenan secretos; `validated_by` es FK al usuario autenticado.

### II. Multi-Tenant Data Isolation ✓
- Toda query sobre `compliance_cell_validations` filtra por `organization_id`.
- El endpoint verifica que `supplier.organization_id == user.organization_id` antes de crear el registro.
- La query bulk de validaciones en `get_annual_compliance()` filtra por `organization_id` y `supplier_id`.

### III. Test-First para Paths Críticos ✓ (N/A)
- Esta entrega no cubre autenticación, autorización ni facturación. Los controles de autorización heredan los mecanismos ya probados de spec 001.

### IV. Simplicity and Iteration (YAGNI) ✓
- Nueva tabla mínima (5 columnas útiles + audit). No se agrega abstracción de repositorio ni capa de caché.
- No se implementa "desvalidar" el tipo desde el visualizador (fuera de scope).
- La query de validaciones se agrega a `get_annual_compliance()` existente; no se crea un nuevo servicio.

## Project Structure

### Documentation (this feature)

```text
specs/008-multi-upload-doc-viewer/
├── plan.md              ← Este archivo
├── research.md          ← Decisiones de diseño Phase 8
├── data-model.md        ← Entidad ComplianceCellValidation + CellOut actualizado
├── contracts/
│   └── compliance-validate.md  ← Contrato del nuevo endpoint
└── tasks.md             ← Tareas T001-T034 (T027-T034 pendientes)
```

### Source Code

```text
backend/
├── src/repse/
│   ├── compliance/
│   │   ├── models.py          ← NUEVO: ComplianceCellValidation
│   │   ├── routes.py          ← NUEVO endpoint POST /compliance/validate
│   │   ├── schemas.py         ← CellOut.type_validated: bool
│   │   └── service.py         ← get_annual_compliance() + cell_status() actualizados
│   └── alembic/
│       └── versions/
│           └── 0004_add_compliance_cell_validations.py  ← NUEVA migración
└── alembic/
    └── env.py                 ← import repse.compliance.models

frontend/
└── src/
    ├── lib/api/
    │   └── documents.ts       ← validateDocumentType()
    └── components/
        ├── documents/
        │   └── DocumentViewerModal.tsx  ← Botón "Marcar como Validado"
        └── suppliers/
            └── ComplianceGrid.tsx       ← type_validated en ViewerState
```

**Structure Decision**: Web application (backend + frontend). El nuevo código vive en los módulos `compliance/` (backend) y `documents/` + `suppliers/` (frontend) ya existentes. No se crean módulos nuevos.

## Complexity Tracking

No hay violaciones de la constitución. La nueva tabla es la opción más simple para almacenar estado de validación por tipo (ver `research.md §1`).
