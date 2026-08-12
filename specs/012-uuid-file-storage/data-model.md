# Data Model: UUID Suffix en Nombres de Archivo

**Feature**: 012-uuid-file-storage | **Date**: 2026-06-08

---

## Entidades afectadas

### Document (`documents` table) — Sin cambios de esquema

El campo `file_path` ya existe como `VARCHAR(1024)`. No se requiere ninguna migración de base de datos.

| Campo | Tipo | Antes | Después |
|---|---|---|---|
| `file_path` | `VARCHAR(1024)` | `"1/42/317/v1.pdf"` | `"1/42/317/v1.550e8400-e29b-41d4-a716-446655440000.pdf"` |

La longitud máxima de la nueva ruta es ~75 caracteres, bien dentro del límite de 1024.

---

## Estructura del StoredFile (valor de retorno)

`StoredFile` es una dataclass inmutable definida en `storage.py`. No cambia su definición; solo cambia el valor que devuelve `relative_path`.

```
StoredFile
  relative_path: str   # ahora contiene UUID4 en el nombre
  size_bytes:    int
  sha256_hex:    str
```

---

## Formato de ruta en disco

```
UPLOAD_ROOT/
└── {organization_id}/           # e.g. "1"
    └── {supplier_id}/           # e.g. "42"
        └── {document_id}/       # e.g. "317"
            ├── v1.pdf           ← archivos existentes (sin UUID, siguen funcionando)
            └── v2.550e8400-e29b-41d4-a716-446655440000.pdf  ← nuevos archivos
```

---

## Transiciones de estado relevantes

No hay transiciones de estado nuevas. El ciclo de vida del documento no cambia:

```
pending → stored (file_path actualizado con UUID) → is_latest=False (nueva versión) → deleted_at set
```

---

## Sin nuevas tablas ni migraciones Alembic

Esta feature no requiere archivo de migración Alembic. El esquema de base de datos no cambia.
