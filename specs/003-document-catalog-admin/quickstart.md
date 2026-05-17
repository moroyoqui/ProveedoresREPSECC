# Quickstart: Administración de Catálogos

Asume el stack del [spec 001](../001-repse-compliance-tracker/quickstart.md) corriendo. Este spec no requiere infraestructura adicional: solo extiende módulos existentes y agrega vistas en el frontend.

## Prerrequisitos

- Stack del 001 levantado (`docker compose up`).
- Sesión admin (rol `admin`) en el tenant de prueba.

## Aplicar migraciones de 003

No hay migrations nuevas de schema (todas las tablas existen ya en el baseline del 001).

```bash
docker compose restart app
# La app arranca sin migrations pendientes.
```

## Smoke test (US1 → US4 del spec)

### US1: desactivar un canónico

```bash
# Listar canónicos activos
curl https://localhost/api/v1/document-types -b cookies.txt | jq '.items[].slug'

# Desactivar ICSOE
curl -X POST https://localhost/api/v1/document-types/4/archive \
  -b cookies.txt -H "Content-Type: application/json" \
  -d '{ "reason": "No aplica a nuestra operación" }'

# Verificar que dejó de ofrecerse al asignar requisitos
curl https://localhost/api/v1/document-types -b cookies.txt | jq '.items[] | select(.slug=="icsoe")'
# (no debería aparecer en "active")
```

### US2: crear un DocumentType personalizado

```bash
curl -X POST https://localhost/api/v1/document-types \
  -b cookies.txt -H "Content-Type: application/json" \
  -d '{
    "name": "Constancia interna de seguridad e higiene",
    "description": "Documento interno SST",
    "periodicity": "bimonthly"
  }'
# 201 { id: 102, ..., origin: "custom" }
```

### US3: crear un SupplierType

```bash
curl -X POST https://localhost/api/v1/supplier-types \
  -b cookies.txt -H "Content-Type: application/json" \
  -d '{
    "name": "Construcción",
    "description": "Empresas de servicios de construcción"
  }'
# 201 { id: 3, ..., origin: "custom" }
```

### US4: definir requisitos del SupplierType

```bash
# Asignar 4 requisitos heredados
for slug in opinion-sat opinion-imss opinion-infonavit cfdi-nomina; do
  curl -X POST https://localhost/api/v1/supplier-types/3/requirements \
    -b cookies.txt -H "Content-Type: application/json" \
    -d "{ \"document_type_id\": $(get_id $slug), \"periodicity_override\": null }"
done

# Override de periodicidad
curl -X PATCH https://localhost/api/v1/supplier-type-requirements/52 \
  -b cookies.txt -H "Content-Type: application/json" \
  -H "If-Match: \"2026-05-17T10:00:00.123456Z\"" \
  -d '{ "periodicity_override": "bimonthly" }'
# 200 con periodicity_effective = "bimonthly"
```

> **Nota**: el wizard "Importar plantilla por industria" (US5 en versiones previas del spec) está fuera de scope para v1. El admin construye sus tipos de proveedor manualmente con US3 + US4.

## Validación de side effects

Después de cualquier mutación al catálogo, validar:

1. **Bitácora**:
   ```bash
   curl "https://localhost/api/v1/audit-log?entity_type=supplier_type" -b cookies.txt | jq '.items[0]'
   # Debería incluir el cambio recién hecho
   ```

2. **Recálculo de cumplimiento**: el background task corre en <60 s para un tenant de 500 proveedores. Validar con un proveedor afectado:
   ```bash
   curl https://localhost/api/v1/suppliers/12 -b cookies.txt | jq '.compliance_percent, .counts'
   # Refleja el nuevo conjunto de requisitos
   ```

3. **Multi-tenant aislado**: con sesión de otro tenant, GET sobre el `SupplierType` creado debe responder 404.

## Operación

| Tarea | Comando |
|-------|---------|
| Ver canónicos nuevos pendientes de activar | `curl /api/v1/document-types/canonical-updates -b cookies.txt` |
| Recálculo manual del tenant | `docker compose exec app python -m repse.documents.recalculator --org 7` |

## Tests automatizados

```bash
# Backend
docker compose exec app pytest tests/contract/test_catalog_admin_contracts.py -v
docker compose exec app pytest tests/integration/test_supplier_type_archive_with_suppliers.py -v
docker compose exec app pytest tests/integration/test_system_type_immutable.py -v

# Frontend
docker compose exec frontend pnpm vitest run src/pages/settings/catalogs/
docker compose exec frontend pnpm playwright test tests/e2e/us3_create_supplier_type.spec.ts
```

## Recuperación de incidentes

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| El admin cambia una periodicidad y el dashboard no refleja el cambio | BackgroundTask de recálculo falló | Ejecutar recálculo manual `python -m repse.documents.recalculator --org N` |
| Proveedores con "tipo archivado" no se pueden reclasificar | UI mostrando solo tipos `status='active'` | Confirmar `PATCH /suppliers/{id} { supplier_type_id: X }` con un tipo activo |
| PATCH responde `409 stale_update` | Otro admin editó al mismo tiempo | Refrescar el GET previo y reintentar con el nuevo `If-Match` |

## Próximos pasos en el flujo Spec Kit

- `/speckit-tasks` para descomponer este plan.
- `/speckit-implement` para ejecutar.
