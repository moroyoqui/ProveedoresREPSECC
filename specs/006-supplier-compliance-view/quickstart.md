# Quickstart: Vista de Cumplimiento Anual del Proveedor

Este spec no requiere cambios al entorno local. Hereda el setup del [quickstart del 001](../001-repse-compliance-tracker/quickstart.md).

## Probar el endpoint manualmente

Con el stack levantado (`docker compose up`):

```bash
# 1. Obtener token de sesión (login con Google/Microsoft en el navegador,
#    luego copiar la cookie de sesión)

# 2. Llamar al endpoint de compliance para el proveedor con id=12, año 2026
curl -s \
  -H "Cookie: session=<tu_cookie>" \
  "http://localhost:8000/api/v1/suppliers/12/compliance?year=2026" \
  | python -m json.tool
```

## Datos de prueba

El script de fixtures `backend/tests/conftest.py` ya incluye factories para `Supplier`, `DocumentType`, `SupplierTypeDocumentRequirement` y `Document`. Para probar la cuadrícula con datos variados:

```python
# Dentro de un test pytest
supplier = SupplierFactory(organization=org, supplier_type=supplier_type)
# Documentos en distintos estados
DocumentFactory(supplier=supplier, document_type=dt_monthly,
                coverage_period_start=date(2026, 1, 1), verified=True)
DocumentFactory(supplier=supplier, document_type=dt_monthly,
                coverage_period_start=date(2026, 2, 1), verified=False)
# Mes 3 → missing (sin documento)
```

## Ejecutar solo los tests de compliance

```bash
# Unit tests de cell_status
pytest backend/tests/unit/test_compliance_service.py -v

# Integration tests del endpoint
pytest backend/tests/integration/test_compliance_routes.py -v
```
