# Research: Portal del Proveedor — Visor de Documentación

**Feature**: 009-proveedor-portal-viewer  
**Date**: 2026-05-20 (actualizado con US5 y US6)

---

## Decision 1: Vinculación del usuario proveedor al `Supplier`

**Decision**: Agregar columna nullable `supplier_id` (FK → `suppliers.id`) en la tabla `users`. Esta columna solo se popula para usuarios con rol `supplier`.

**Rationale**: La alternativa de crear una tabla de enlace separada (`user_supplier_links`) sería sobre-ingeniería para v1, donde la relación es siempre 1:1 (un usuario proveedor = un proveedor). Agregar el FK directo en `users` es más simple y consistente con el patrón ya existente (`organization_id` en la misma tabla).

**Alternatives considered**:  
- Tabla `user_supplier_links` (M:M): permite multi-empresa por usuario en el futuro, pero añade complejidad innecesaria para v1.  
- Campo `metadata JSON`: tipado débil, difícil de indexar o hacer FK constraint.

---

## Decision 2: Nuevo rol `supplier` en el enum `Role`

**Decision**: Extender `Role` (StrEnum en `users/models.py`) con el valor `"supplier"`.

**Rationale**: El sistema ya usa `Role` como string discriminador en el sistema de sesión. Agregar `supplier` al enum es la mínima superficie necesaria; el `require_role()` existente aplica sin cambios.

**Alternatives considered**:  
- Campo booleano `is_supplier` en `User`: no se integra bien con el mecanismo de `require_role()` ya implementado.  
- Rol fijo `"viewer"` con campo extra: rompería el principio de mínimo privilegio; un viewer tendría acceso al módulo de administración.

---

## Decision 3: `supplier_id` en el payload de sesión

**Decision**: Extender `SessionPayload` con `supplier_id: int | None`. En `SessionManager.issue()` y `read()` se serializa/deserializa como campo opcional (backward-compatible: si está ausente en una cookie existente se lee como `None`).

**Rationale**: El portal endpoint debe obtener el `supplier_id` del contexto autenticado del servidor, no de la URL ni del cuerpo de la petición. De lo contrario un usuario podría pasar un `supplier_id` arbitrario. Pasar el `supplier_id` por sesión es la misma solución que ya se usa para `organization_id`.

**Alternatives considered**:  
- Leer `supplier_id` desde la BD en cada petición del portal (join `users → suppliers`): funciona, pero añade una query extra en cada request. La sesión ya tiene TTL firmado; incluir el FK es trivial y más rápido.

---

## Decision 4: Endpoint del portal en router separado `/portal`

**Decision**: Nuevo módulo `repse/portal/routes.py` con prefijo `/api/v1/portal`. El endpoint `GET /portal/compliance` llama a `compliance.service.get_annual_compliance()` con el `supplier_id` de la sesión, sin ningún parámetro de ruta.

**Rationale**: Separa el plano de acceso del proveedor del plano administrativo (`/api/v1/suppliers/{id}/compliance`). La autorización es diferente: el supplier no pasa un ID, el sistema lo impone desde la sesión. Reusar el servicio existente evita duplicar lógica de negocio.

**Alternatives considered**:  
- Reusar el endpoint existente `GET /suppliers/{id}/compliance` con un guard de rol supplier: el proveedor tendría que conocer su `supplier_id` y pasarlo en la URL, lo que abre superficie de ataque de acceso a datos de otros proveedores.

---

## Decision 5: Carga de documentos desde el portal (US5)

**Decision**: Agregar `POST /api/v1/portal/upload` que reutiliza el servicio de documentos existente (`documents/service.py`) pero restringido al propio `supplier_id` de la sesión. El portal valida que el período sea ≤ mes actual y que el estado actual de la celda sea `missing` o `expired`. No se permiten cargas para períodos futuros ni para celdas en estado `submitted`, `validated`, o `expiring_soon`.

**Rationale**: Delegar la carga al servicio existente evita duplicar lógica de almacenamiento, validación de formato/tamaño y versionado. La única capa adicional es la autorización de rol+supplier y la validación de estado de celda. Coherente con el principio YAGNI.

**Alternatives considered**:  
- Endpoint de carga completamente independiente: duplicaría validaciones de formato, almacenamiento de archivo y versionado ya probados en el servicio admin.
- Reutilizar `POST /documents` con filtros: el endpoint admin acepta cualquier `supplier_id` en el body; reutilizarlo implicaría que el proveedor podría cargar en nombre de otro proveedor si no se valida correctamente.

---

## Decision 6: Redirección al portal en el frontend

**Decision**: En `RequireAuth` y en la ruta raíz del router, usuarios con `role === "supplier"` son redirigidos a `/portal`. El `AppShell` para ese rol muestra solo el enlace al portal y el botón de logout.

**Rationale**: Los proveedores no deben ver ni poder navegar a secciones administrativas. La redirección es la forma más simple de aislar la experiencia sin duplicar toda la capa de autenticación. Se puede implementar extendiendo el `<Navigate>` actual con una condición de rol.

---

## Decision 7: Reutilizar `ComplianceGridOut` como DTO del portal

**Decision**: El portal endpoint devuelve exactamente `ComplianceGridOut`, el mismo schema que usa el endpoint admin.

**Rationale**: El modelo de datos de cumplimiento ya contiene todo lo que el proveedor necesita ver (estado por tipo de documento, celdas mensuales, requisitos one-time). Crear un DTO diferente sería YAGNI. El frontend puede reutilizar lógica de formateo y badges.

---

## Decision 8: Nueva tabla `portal_submissions` para el flujo de envío a validación (US6)

**Decision**: Nueva tabla `portal_submissions` que registra el envío de un tipo de documento + período por parte del proveedor. Campos clave: `supplier_id`, `document_type_id`, `coverage_period_start` (NULL para documentos únicos), `submitted_at`, `submitted_by`, `status` (pending/approved/rejected), `rejection_reason`, `pre_submission_status` (missing/expired — estado anterior al envío para poder revertir correctamente). No se aplica constraint UNIQUE a nivel de BD; la lógica de negocio garantiza que solo existe una fila con `status = 'pending'` por celda en cada momento.

**Rationale**: 
- Separar la tabla de submissions de `compliance_cell_validations` mantiene la semántica limpia: `ComplianceCellValidation` es para aprobaciones explícitas de supervisor; `portal_submissions` es para solicitudes de revisión iniciadas por el proveedor.
- Requiere `pre_submission_status` para poder revertir al estado correcto si contabilidad rechaza (FR-021).
- Registra `submitted_at` para que contabilidad pueda priorizar por antigüedad (FR-022).
- Sin constraint UNIQUE en BD: permite múltiples rondas de envío/rechazo/re-envío manteniendo historial. El status 'pending' único por celda se valida en la capa de aplicación.

**Alternatives considered**:  
- Extender `ComplianceCellValidation` con campos de submission: mezcla semántica (aprobaciones admin vs. solicitudes supplier); haría más compleja la query de estado de celda.
- Agregar `submitted_at` directamente al `Document`: un tipo de documento puede tener múltiples archivos por período; no hay un único documento al que anclar el envío; la tabla de submissions es más clara.
- Flag `is_submitted` en `Document`: no soporta múltiples archivos por período enviados como paquete, ni el motivo de rechazo, ni el historial de rondas.

---

## Decision 9: Endpoint `POST /portal/submit/{document_type_id}` para envío a validación

**Decision**: Endpoint específico para cambiar el estado de una celda a "pendiente de validación". Recibe `coverage_period_start` en el body (o null para documentos únicos). Valida que: (a) haya al menos un documento cargado en esa celda, (b) la celda no esté ya en estado `submitted`, (c) la celda no esté en estado `validated`. Crea un registro en `portal_submissions` con `status='pending'` y `submitted_at=utcnow()`.

**Rationale**: Separar el endpoint de carga del de envío a validación mantiene la acción de "soy proveedor y ya cargué todo, enviar a revisión" explícita e independiente del upload. Esto corresponde directamente al flujo descrito en US6: primero se cargan archivos, luego se presiona "Enviar a validar" como acción deliberada.

**Alternatives considered**:  
- Envío automático al cargar: contrario al spec (US6 requiere acción explícita del proveedor); el proveedor puede querer cargar múltiples archivos antes de enviar.
- Usar PATCH en el documento para cambiar un campo `is_submitted`: no aplica al nivel de tipo+período; no registra metadatos de submission.

---

## Decision 10: Actualización del `cell_status()` para reflejar `portal_submissions`

**Decision**: La función `compliance.service.get_annual_compliance()` recibirá un conjunto de celdas pendientes de validación (`pending_submissions`) consultado en una query adicional sobre `portal_submissions`. Si una celda está en ese conjunto, su status se retorna como `CellStatus.SUBMITTED`, independientemente del estado del `Document` individual.

**Rationale**: La lectura del grid ya realiza dos queries consolidadas; agregar una tercera query para submissions pendientes mantiene la misma arquitectura. Consultar submissions dentro del servicio centraliza la lógica de estado en un solo lugar en lugar de distribuirla en el endpoint de portal.

**Alternatives considered**:  
- Consultar submissions en el router del portal y parcharlos sobre el grid: duplica lógica de celda; más difícil de probar.
- Campo `is_submitted` en `Document`: no funciona cuando hay múltiples archivos por celda; la submission es una operación a nivel de (tipo+período), no de archivo individual.

---

## Unknowns resueltos

| Pregunta | Respuesta |
|---|---|
| ¿Se necesita tabla nueva para la relación usuario-proveedor? | No; FK nullable en `users.supplier_id` es suficiente para v1 |
| ¿El portal endpoint requiere nueva lógica de negocio? | No para lectura; sí para upload (POST /portal/upload) y submit (POST /portal/submit) |
| ¿La sesión necesita cambios breaking? | No; `supplier_id` se agrega como campo opcional backward-compatible |
| ¿Se necesita migración de datos? | Sí para `portal_submissions`; la columna `users.supplier_id` es nullable con default NULL |
| ¿Puede el proveedor cargar múltiples archivos por celda? | Sí, con máximo configurable en el catálogo de tipos de documento |
| ¿La interfaz de aprobación/rechazo de contabilidad está en scope? | No — solo el modelo de datos y el endpoint de submit; la UI de contabilidad es feature separada |
| ¿Qué pasa cuando contabilidad rechaza? | Estado regresa al `pre_submission_status` registrado en `portal_submissions`; motivo de rechazo visible al proveedor; carga y re-envío habilitados |
| ¿Puede el proveedor cargar mientras está en Pendiente de validación? | No — la carga está bloqueada hasta que contabilidad resuelva |
