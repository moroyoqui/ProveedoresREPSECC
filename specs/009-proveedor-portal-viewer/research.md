# Research: Portal del Proveedor — Visor de Documentación

**Feature**: 009-proveedor-portal-viewer  
**Date**: 2026-05-19

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

## Decision 5: Portal de solo lectura en v1

**Decision**: El proveedor no puede cargar, editar ni eliminar documentos desde el portal en v1. El portal es estrictamente de lectura.

**Rationale**: El spec lo establece explícitamente como supuesto de v1. Simplifica los permisos (el rol `supplier` no necesita acceso a endpoints de escritura de documentos) y reduce la superficie de revisión de seguridad.

---

## Decision 6: Redirección al portal en el frontend

**Decision**: En `RequireAuth` y en la ruta raíz del router, usuarios con `role === "supplier"` son redirigidos a `/portal`. El `AppShell` para ese rol muestra solo el enlace al portal y el botón de logout.

**Rationale**: Los proveedores no deben ver ni poder navegar a secciones administrativas. La redirección es la forma más simple de aislar la experiencia sin duplicar toda la capa de autenticación. Se puede implementar extendiendo el `<Navigate>` actual con una condición de rol.

---

## Decision 7: Reutilizar `ComplianceGridOut` como DTO del portal

**Decision**: El portal endpoint devuelve exactamente `ComplianceGridOut`, el mismo schema que usa el endpoint admin.

**Rationale**: El modelo de datos de cumplimiento ya contiene todo lo que el proveedor necesita ver (estado por tipo de documento, celdas mensuales, requisitos one-time). Crear un DTO diferente sería YAGNI. El frontend puede reutilizar lógica de formateo y badges.

---

## Unknowns resueltos

| Pregunta | Respuesta |
|---|---|
| ¿Se necesita tabla nueva para la relación usuario-proveedor? | No; FK nullable en `users.supplier_id` es suficiente para v1 |
| ¿El portal endpoint requiere nueva lógica de negocio? | No; reutiliza `compliance.service.get_annual_compliance()` íntegramente |
| ¿La sesión necesita cambios breaking? | No; `supplier_id` se agrega como campo opcional backward-compatible |
| ¿Se necesita migración de datos? | No; la columna es nullable con default NULL |
