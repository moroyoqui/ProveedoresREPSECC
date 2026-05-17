# Phase 0 Research: Administración de Catálogos

Hereda del [research del 001](../001-repse-compliance-tracker/research.md) todo el stack y los patrones de multi-tenant + bitácora. Aquí solo se resuelven los unknowns específicos de la administración de catálogos.

> **Nota 2026-05-17**: el wizard "Importar plantilla por industria" se removió del scope. Las decisiones §1 (plantillas en código vs DB), §2 (snapshot copy vs live link) y §7 (validación de slugs) que vivían en versiones previas se eliminaron junto con la feature.

---

## 1. Notificación al admin cuando aparece un canónico nuevo

**Decisión**: reutilizar la **tabla `notifications`** del [spec 002](../002-compliance-alerts/spec.md) con `alert_type='catalog_canonical_added'` y `payload_json = { document_type_slug, document_type_name }`. Si el spec 002 aún no está mergeado al implementar 003, se crea una tabla temporal `system_notifications` con la misma forma y luego se migra al schema unificado del 002.

**Rationale**:
- No duplicar centros de notificación (1 solo para todo el producto).
- El admin abre el panel y ve las novedades junto con las alertas operativas.
- Cero canales nuevos.

**Trigger**: cuando una migration Alembic posterior a la baseline agrega un `DocumentType` canónico (`origin='canonical'`, `organization_id IS NULL`), el código de la migration emite una notificación in-app para todos los admins de todos los tenants existentes. Tenants nuevos lo reciben automáticamente activado (FR-012 del spec).

**Alternativas**:
- Correo separado: spammy y el admin puede tener correos silenciados.
- Banner global en la UI: invasivo, fácil de ignorar.

---

## 2. Recálculo de cumplimiento tras cambios en el catálogo

**Decisión**: cualquier cambio en el catálogo que modifique los requisitos efectivos de uno o más proveedores dispara un **recálculo asíncrono** del status de sus documentos, ejecutado en `FastAPI BackgroundTask` dentro del request handler que provocó el cambio.

**Eventos que disparan recálculo**:
| Evento | Subconjunto afectado |
|--------|----------------------|
| Activar/desactivar un `DocumentType` del catálogo | Todos los proveedores cuyos `SupplierType` referencien ese type. |
| Crear / editar / eliminar / archivar un `DocumentType` personalizado | Todos los proveedores cuyos `SupplierType` lo referencien. |
| Crear / editar / eliminar un `SupplierTypeDocumentRequirement` | Solo proveedores con ese `SupplierType`. |
| Cambiar `periodicity_override` de un requisito | Solo proveedores con ese `SupplierType`; los documentos previamente cargados se reevalúan con la nueva periodicidad. |
| Archivar un `SupplierType` | Los proveedores asociados se marcan como "tipo archivado" y dejan de contar al agregado. |

**Implementación**:
```python
async def update_requirement(req_id: int, ...):
    req = await db.get(SupplierTypeDocumentRequirement, req_id)
    req.periodicity_override = new_value
    await db.commit()
    # Async: recalcular estado de todos los documentos afectados
    background_tasks.add_task(
        recalc_documents_for_supplier_type,
        organization_id=req.organization_id,
        supplier_type_id=req.supplier_type_id,
    )
```

**Alternativas**:
- Síncrono: timeouts si hay miles de documentos.
- Cron periódico: el admin no ve el efecto inmediato; mala UX ("¿se aplicó mi cambio?").
- Cola externa (Celery): YAGNI; BackgroundTasks cubre el caso.

---

## 3. Reasignación masiva al archivar un `SupplierType`

**Decisión**: NO se implementa "reasignación masiva en una sola operación" en v1. Si el admin archiva un tipo con proveedores asociados, los proveedores quedan con `supplier_type_id` apuntando al tipo archivado y se marcan visualmente como "tipo archivado, reclasificar". El admin ve una tarea pendiente en el centro de notificaciones del 002 y reclasifica caso por caso (`PATCH /suppliers/{id} { supplier_type_id: ... }`).

**Rationale**:
- Una reasignación masiva exige UI compleja (¿asignar a qué tipo? ¿uno fijo para todos, o por filtro?). YAGNI v1.
- La cantidad de proveedores afectados suele ser baja (≤20). Reclasificar uno a uno toma <2 min.
- La regla "tipo archivado no se cuenta en el agregado" mantiene la métrica del tenant en buen estado mientras se hace la reclasificación.

**Alternativas**:
- Modal "Asignar todos a otro tipo": se considera para v2 si el feedback lo pide.
- Bloqueo de archivar mientras haya proveedores: muy estricto; el admin sabe lo que hace y debe poder archivar.

---

## 4. Concurrencia y locks al editar el mismo catálogo

**Decisión**: optimistic concurrency via `updated_at` token. Cada `PATCH` envía el `updated_at` que recibió en el GET previo; si no coincide al guardar, responde `409 stale_update`.

**Rationale**:
- Caso real: dos admins editan el mismo `SupplierType` al mismo tiempo. Sin protección, el último gana silenciosamente.
- `updated_at` ya existe en todas las tablas. Sin nuevos campos.

**Implementación**: header `If-Match: "2026-05-17T15:23:11.000123Z"` en PATCH, o campo `expected_updated_at` en body. Si el servidor detecta divergencia, responde 409 con el estado actual para que el cliente refresque y reintente.

**Alternativas**:
- Pessimistic lock: requeriría tabla de locks o `SELECT FOR UPDATE`; complica el modelo y abre la puerta a locks olvidados.
- Last-write-wins silencioso: pérdida de cambios sin avisar; mala UX.

---

## Resumen

| Tema | Decisión | Sección |
|------|----------|---------|
| Notificación de canónico nuevo | Reusa tabla `notifications` del spec 002 | §1 |
| Recálculo de cumplimiento | Async via FastAPI BackgroundTask, segmentado por tenant + supplier type | §2 |
| Reasignación masiva al archivar | NO en v1; reclasificación caso a caso | §3 |
| Concurrencia | Optimistic con `updated_at` token, 409 si stale | §4 |
