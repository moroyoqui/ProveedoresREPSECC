# API Contracts: Administración de Catálogos

Endpoints específicos del spec 003. Las convenciones globales heredan del [contracts/README del 001](../../001-repse-compliance-tracker/contracts/README.md).

Este spec **extiende** dos dominios cuyos endpoints de lectura ya están definidos en el 001:

- [001/contracts/document-types.md](../../001-repse-compliance-tracker/contracts/document-types.md) — solo lectura del catálogo.
- [001/contracts/supplier-types.md](../../001-repse-compliance-tracker/contracts/supplier-types.md) — endpoints definidos por adelantado durante el plan del 001. La **implementación** de los write endpoints (POST/PATCH/DELETE/archive/restore + requirements) **pertenece a este spec 003**. Los endpoints de plantillas (`/supplier-type-templates`) definidos en ese archivo quedan **fuera de scope de v1** tras la decisión del 2026-05-17 y NO se implementan en 003.

| Archivo | Cobertura |
|---------|-----------|
| [document-types-admin.md](./document-types-admin.md) | CRUD de tipos de documento personalizados + activación de canónicos por tenant. |
| [supplier-types-admin.md](./supplier-types-admin.md) | CRUD de tipos de proveedor (extiende contracts/supplier-types.md del 001). |
| [requirements-admin.md](./requirements-admin.md) | CRUD de asociaciones `SupplierType ↔ DocumentType` con override de periodicidad. |

## Encabezado obligatorio: `If-Match` en mutations

Todos los `PATCH` y `DELETE` sobre entidades de catálogo (`DocumentType`, `SupplierType`, `SupplierTypeDocumentRequirement`) DEBEN incluir el header:

```http
If-Match: "<updated_at_iso8601>"
```

Donde `<updated_at_iso8601>` es el `updated_at` recibido en el GET previo. Si no coincide con el valor actual en DB, el servidor responde `409 stale_update` con el cuerpo actual para que el cliente refresque y reintente.

## Tests de contrato (obligatorios por constitución)

Para cada endpoint:

1. **Forma de respuesta**.
2. **Auth required** (401 sin sesión).
3. **Multi-tenant negativo** (404 con sesión de otro tenant).
4. **Rol insuficiente** (403 para viewer/manager en endpoints admin).
5. **Optimistic concurrency**: PATCH/DELETE sin `If-Match` o con valor stale → 409.
6. **Side effects auditados**: cada mutation crea una fila en `audit_log` con la acción correspondiente.
