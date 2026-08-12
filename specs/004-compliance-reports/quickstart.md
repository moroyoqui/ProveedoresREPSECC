# Quickstart: Reportes Exportables de Cumplimiento

## Dependencias nuevas

Backend (`backend/pyproject.toml` / requirements):

- `weasyprint` — render de PDF desde HTML/CSS.
- `jinja2` — plantillas del PDF (si no está ya como dependencia transitiva de FastAPI/Starlette, declararla explícitamente).

CSV, ZIP y zona horaria usan la **stdlib** (`csv`, `zipfile`, `zoneinfo`) — sin dependencias.

### Libs nativas de WeasyPrint (Docker)

WeasyPrint requiere Pango/Cairo/GDK-Pixbuf. Añadir al `Dockerfile` del backend (Debian/Ubuntu):

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
```

## Configuración (variables de entorno)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `REPORTS_ASYNC_SUPPLIER_THRESHOLD` | `50` | Nº de proveedores por encima del cual la exportación es asíncrona. |
| `REPORTS_ASYNC_DOCUMENT_THRESHOLD` | `1000` | Nº de documentos por encima del cual es asíncrona. |
| `REPORTS_LINK_TTL_HOURS` | `24` | Horas de validez del enlace de descarga. |
| `REPORTS_ZIP_MAX_BYTES` | `2147483648` | Tamaño máximo del ZIP (2 GB). |
| `REPORTS_STORAGE_DIR` | `var/exports` | Directorio en disco de los archivos generados. |
| `REPORTS_TENANT_TZ_DEFAULT` | `America/Mexico_City` | Zona horaria por defecto del tenant. |

## Migración de base de datos

Crear la tabla `export_request` (ver [data-model.md](./data-model.md)). Usar el mecanismo de migraciones del proyecto.

## Flujo de verificación manual

1. **Sync, un proveedor (CSV)**: en el detalle de un proveedor con documentos en estados mixtos, exportar CSV → descarga inmediata; una fila por documento esperado, "Faltante" incluido. *(US1)*
2. **PDF**: exportar el mismo proveedor en PDF → encabezado del tenant, zona horaria visible, tabla legible. *(US1 AC2)*
3. **Filtrado, varios proveedores**: filtrar el listado por estado y exportar → el archivo contiene solo los proveedores filtrados. *(US2)*
4. **Async (umbral)**: exportar con > 50 proveedores → respuesta `202 pending`; la UI hace polling y muestra notificación al pasar a `ready`; descarga válida ≥ 24 h. *(US2 AC2)*
5. **ZIP con originales**: exportar con `include_originals` → ZIP con resumen en la raíz, carpeta por proveedor y archivos `{tipo}_{periodo}_{fecha-carga}.{ext}`. *(US3)*
6. **Aislamiento**: intentar descargar el `id` de otro tenant → `404`. Sin sesión → `401`. Enlace vencido → `410`. *(SC-004 / SC-006)*

## Tests

```bash
# Backend (desde la raíz, con backend/.venv)
pytest backend/tests/contract/test_reports_contract.py
pytest backend/tests/integration/test_reports_export.py
pytest backend/tests/integration/test_reports_tenant_isolation.py
pytest backend/tests/integration/test_reports_async.py
pytest backend/tests/unit/test_reports_renderers.py
```

Prioridad de tests-first (Constitución III): aislamiento multi-tenant y autorización de descarga antes del merge.
