# Implementation Plan: Administración de Catálogos (Documentos + Proveedores)

**Branch**: `003-document-catalog-admin` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from [./spec.md](./spec.md)

**Note**: Plan generado por `/speckit-plan`. Hereda el stack del [plan del spec 001](../001-repse-compliance-tracker/plan.md). Las entidades `DocumentType`, `SupplierType` y `SupplierTypeDocumentRequirement` ya están definidas en el [data-model del 001](../001-repse-compliance-tracker/data-model.md); este spec añade lo necesario para administrarlas vía UI/API y para soportar el wizard de plantillas por industria.

## Summary

Construir las dos secciones de "Catálogos" en la UI del cliente contratante (admin only): tipos de documento (activar/desactivar canónicos + crear personalizados) y tipos de proveedor (CRUD del catálogo del tenant + asociación de requisitos con override de periodicidad). El admin configura todo manualmente. Sin nueva tecnología: solo aprovecha el stack del 001. (El wizard "Importar plantilla por industria" se removió del scope el 2026-05-17 y se postpuso a una fase posterior.)

## Technical Context

Hereda íntegramente del [plan 001](../001-repse-compliance-tracker/plan.md). Cambios mínimos:

**Language/Version**: sin cambios (Python 3.12 + TS 5.4).

**Primary Dependencies (nuevas)**:
- **Backend**: ninguna lib nueva. Toda la funcionalidad se cubre con FastAPI + SQLAlchemy + Pydantic que ya hay.
- **Frontend**: `dnd-kit` o `react-beautiful-dnd` opcional para drag-drop al ordenar requisitos. Decisión: NO usar drag-drop en v1 (botones "subir / bajar" simples). YAGNI.

**Storage**: mismas tablas del 001 (`document_types`, `tenant_document_type_settings`, `supplier_types`, `supplier_type_document_requirements`). Adiciones nuevas:
- **Notificaciones de catálogo canónico actualizado** (FR-012 del spec): reutiliza `Notification` del [spec 002](../002-compliance-alerts/spec.md) si está mergeado; si no, se crea una tabla `system_notifications` simple para este spec.

**Testing**: pytest + factory_boy. Tests críticos: aislamiento multi-tenant del catálogo, regla "Sin clasificar inmutable", archivado de tipo de proveedor con proveedores asociados.

**Target Platform**: sin cambios.

**Project Type**: web app — extiende `backend/src/repse/document_types/` y `backend/src/repse/supplier_types/` del 001 + agrega rutas de admin; frontend agrega una sección completa "Catálogos".

**Performance Goals**:
- SC-001 (003): admin desactiva tipos + crea custom en <3 min.
- SC-002 (003): primer SupplierType + 5 requisitos en <5 min.
- Cualquier CRUD del catálogo: <500 ms percibidos.
- Recálculo de cumplimiento tras cambio: <60 s para tenant de 500 proveedores (puede ser async vía background task del FastAPI).

**Constraints**:
- "Sin clasificar" (`origin='system'`) NO puede modificarse desde la UI. Enforce a nivel servicio + UI.
- Cualquier cambio en el catálogo dispara recálculo de cumplimiento (status de documentos) del subconjunto afectado. El recálculo es **idempotente** y **per-tenant**.

**Scale/Scope**:
- Por tenant: ~10–50 tipos de documento (canónicos + personalizados), ~5–20 tipos de proveedor, ~50–500 requisitos en total.

## Constitution Check

*GATE: pasa antes de research. Re-evalúa post-design.*

| Principio | Estado | Cómo se cumple |
|-----------|--------|----------------|
| **I. Secure by Default** | ✅ Pass | Todos los endpoints son admin-only (FR-001). Cambios al catálogo registran user_id en bitácora. |
| **II. Multi-Tenant Data Isolation** | ✅ Pass | `document_types` personalizados, `supplier_types` y `supplier_type_document_requirements` llevan `organization_id` NOT NULL + filtro automático. Test específico: tenant A modifica su catálogo, tenant B no lo nota. |
| **III. Test-First for Critical Paths** | ✅ Pass | Tests obligatorios: multi-tenant isolation, "Sin clasificar" inmutable, propagación de canónico nuevo (FR-012 del spec), archivado con proveedores asociados. |
| **IV. Observability** | ✅ Pass | Cada modificación de catálogo emite audit log (FR-011, FR-018, FR-022). Métricas: `catalog_changes_total{tenant_id,catalog_type}`. |
| **V. Simplicity & YAGNI** | ✅ Pass | Sin DB schema nuevo (todas las entidades existen en 001). Sin lib de drag-drop (botones up/down). Sin orquestador externo: el recálculo es BackgroundTask de FastAPI cuando aplica. Wizard de plantillas postpuesto (no se construye lo que no se ha validado con clientes). |

**Resultado**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-document-catalog-admin/
├── spec.md
├── plan.md                          # Este archivo
├── research.md                      # Phase 0
├── data-model.md                    # Phase 1
├── quickstart.md                    # Phase 1
├── contracts/                       # Phase 1
│   ├── README.md
│   ├── document-types-admin.md      # Endpoints de escritura sobre catálogo de docs
│   ├── supplier-types-admin.md     # Endpoints de escritura sobre catálogo de proveedores
│   └── requirements-admin.md        # Asociaciones SupplierType ↔ DocumentType
├── checklists/requirements.md
└── tasks.md                         # Phase 2 (NO creado aquí)
```

### Source Code (repository root)

Casi todo extiende módulos ya existentes del 001. Añadidos quirúrgicos.

```text
backend/
└── src/repse/
    ├── document_types/                       # YA EXISTE del 001
    │   ├── models.py                         # (sin cambios)
    │   ├── schemas.py                        # (ampliar con DocumentTypeCreateIn, DocumentTypePatchIn)
    │   ├── service.py                        # AMPLIAR: create_custom, archive, restore, activate_canonical, deactivate_canonical
    │   └── routes.py                         # AMPLIAR con endpoints de escritura (POST/PATCH/DELETE)
    ├── supplier_types/                       # YA EXISTE del 001 (read-only por ahora)
    │   ├── models.py                         # (sin cambios; ya tiene SupplierType y SupplierTypeDocumentRequirement)
    │   ├── schemas.py                        # AMPLIAR (Create/Patch/RequirementCreate/RequirementPatch)
    │   ├── service.py                        # AMPLIAR: CRUD de SupplierType, CRUD de requisitos, archive
    │   ├── routes.py                         # AMPLIAR con endpoints de escritura
    │   └── provisioning.py                   # (sin cambios respecto a 001)
    └── catalog_changes/                      # NUEVO módulo cohesivo (opcional)
        └── notifier.py                       # Notificación al admin cuando se agrega un canónico nuevo (FR-012)

frontend/
└── src/
    ├── pages/
    │   └── settings/
    │       └── catalogs/
    │           ├── index.tsx                 # Hub con dos pestañas (Documentos / Tipos de proveedor)
    │           ├── document-types.tsx        # Lista + edición de tipos de documento
    │           ├── supplier-types.tsx        # Lista + edición de tipos de proveedor
    │           └── supplier-type-detail.tsx  # Detalle: requisitos con periodicidad efectiva
    └── components/
        └── catalogs/
            ├── DocumentTypeForm.tsx
            ├── SupplierTypeForm.tsx
            ├── RequirementRow.tsx            # Una fila por requisito (doc type + periodicidad + override)
            └── PeriodicitySelect.tsx         # Selector con "Heredar" + overrides explícitos
```

**Structure Decision**: extender módulos `document_types/` y `supplier_types/` del 001 (donde ya viven los modelos). Frontend agrega una sección "Configuración → Catálogos" con dos pestañas. Cero nuevas tablas: todas las decisiones de modelado quedaron resueltas en el data-model del 001.

## Complexity Tracking

| Decisión | Por qué se aparta del default | Alternativa simple rechazada porque |
|----------|------------------------------|-------------------------------------|
| **Recálculo de cumplimiento en BackgroundTask en lugar de síncrono** | Cambiar la periodicidad efectiva de un requisito puede afectar miles de documentos. Bloquear el request del admin no es aceptable; tampoco lo es no recalcular. | Recálculo síncrono: timeouts en tenants grandes. Worker dedicado (Celery): YAGNI para v1; FastAPI BackgroundTasks cubre el caso. |
| **Sin drag-drop para reordenar requisitos en v1** | No hay requisito funcional que lo exija; los requisitos no tienen orden semántico, solo se muestran ordenados por nombre. | dnd-kit / react-beautiful-dnd agrega ~50KB al bundle sin valor visible. Si más adelante se decide ordenar manualmente, se introduce. |
| **Wizard de plantillas removido del scope** (2026-05-17) | El admin puede armar manualmente sus tipos de proveedor con sus requisitos. Las plantillas eran "nice to have" sin evidencia de demanda. | Implementarlas igual: ~5–7 historias de plantillas curadas + UI de wizard + reglas de merge. ~20% del trabajo total del spec sin valor validado. Si surge demanda, se introduce como spec dedicado. |

---

**Phase 0**: ver [research.md](./research.md).

**Phase 1**: ver [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).
