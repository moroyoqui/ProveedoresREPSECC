# API Contract: Catálogo de Sectores y Giros

**Feature**: 010-sector-giro-catalog
**Date**: 2026-06-08
**Base prefix**: `/api/v1`

---

## Autenticación y autorización

Todos los endpoints requieren sesión autenticada (cookie `session`).

| Método | Rol mínimo requerido |
|--------|---------------------|
| `GET /sectors`, `GET /giros` | Cualquier rol autenticado (`admin`, `manager`, `viewer`; NO `supplier`) |
| `POST`, `PATCH`, `DELETE` en sectores/giros | Solo `admin` |

---

## Sectores

### `GET /sectors`

Lista todos los sectores en orden alfabético.

**Response 200**:
```json
[
  { "id": 1, "name": "Construcción" },
  { "id": 2, "name": "Manufactura" }
]
```

---

### `POST /sectors`

Crea un nuevo sector. Solo `admin`.

**Request body**:
```json
{ "name": "Construcción" }
```

**Validations**:
- `name`: requerido, 2–120 caracteres, unique (case-insensitive).

**Response 201**:
```json
{ "id": 3, "name": "Construcción" }
```

**Error 409** (nombre duplicado):
```json
{ "error": { "code": "sector_name_taken", "message": "Ya existe un sector con ese nombre." } }
```

---

### `PATCH /sectors/{id}`

Edita el nombre de un sector. Solo `admin`.

**Request body**:
```json
{ "name": "Construcción Civil" }
```

**Response 200**:
```json
{ "id": 1, "name": "Construcción Civil" }
```

**Error 404**: sector no encontrado.
**Error 409**: nuevo nombre ya en uso por otro sector.

---

### `DELETE /sectors/{id}`

Elimina un sector. Solo `admin`.

**Response 204**: eliminado correctamente.

**Error 409** (dependencias activas):
```json
{
  "error": {
    "code": "sector_has_dependencies",
    "message": "No se puede eliminar: el sector tiene 3 giro(s) asociado(s)."
  }
}
```

**Error 409** (asignado a proveedores):
```json
{
  "error": {
    "code": "sector_in_use",
    "message": "No se puede eliminar: el sector está asignado a 12 proveedor(es)."
  }
}
```

---

## Giros

### `GET /giros`

Lista giros. Soporta filtro opcional por sector.

**Query params**:
- `sector_id` (opcional, int): filtra giros de ese sector.

**Response 200**:
```json
[
  { "id": 1, "sector_id": 1, "sector_name": "Construcción", "name": "Plomería" },
  { "id": 2, "sector_id": 1, "sector_name": "Construcción", "name": "Obra civil" }
]
```

---

### `POST /giros`

Crea un giro dentro de un sector. Solo `admin`.

**Request body**:
```json
{ "sector_id": 1, "name": "Plomería" }
```

**Validations**:
- `sector_id`: requerido, debe existir en `sectors`.
- `name`: requerido, 2–120 caracteres, único dentro del `sector_id` (case-insensitive).

**Response 201**:
```json
{ "id": 5, "sector_id": 1, "sector_name": "Construcción", "name": "Plomería" }
```

**Error 404**: `sector_id` no existe.
**Error 409**: nombre duplicado en ese sector:
```json
{ "error": { "code": "giro_name_taken", "message": "Ya existe un giro con ese nombre en este sector." } }
```

---

### `PATCH /giros/{id}`

Edita nombre y/o sector de un giro. Solo `admin`.

**Request body** (todos los campos son opcionales):
```json
{ "name": "Plomería industrial", "sector_id": 2 }
```

**Response 200**:
```json
{ "id": 5, "sector_id": 2, "sector_name": "Manufactura", "name": "Plomería industrial" }
```

**Error 404**: giro no encontrado o sector nuevo no existe.
**Error 409**: nombre duplicado en el sector destino.

---

### `DELETE /giros/{id}`

Elimina un giro. Solo `admin`.

**Response 204**: eliminado correctamente.

**Error 409** (asignado a proveedores):
```json
{
  "error": {
    "code": "giro_in_use",
    "message": "No se puede eliminar: el giro está asignado a 5 proveedor(es)."
  }
}
```

---

## Extensión a `/suppliers`

### `GET /suppliers` — nuevos query params

| Param | Tipo | Descripción |
|-------|------|-------------|
| `sector_id` | int (opcional) | Filtra proveedores por sector |
| `giro_id` | int (opcional) | Filtra proveedores por giro (se puede combinar con `sector_id`) |

**Ejemplo**: `GET /suppliers?sector_id=1&giro_id=3`

**Cada item de la lista incluye ahora**:
```json
{
  "id": 42,
  "legal_name": "Constructora XYZ SA de CV",
  "rfc": "CXY010101ABC",
  "sector": { "id": 1, "name": "Construcción" },
  "giro":   { "id": 3, "name": "Obra civil" },
  ...
}
```
Si no tiene clasificación: `"sector": null, "giro": null`.

### `POST /suppliers` y `PATCH /suppliers/{id}` — nuevos campos

```json
{
  "sector_id": 1,
  "giro_id": 3
}
```

**Validaciones adicionales**:
- Si `giro_id` se provee sin `sector_id`: error 422 `giro_requires_sector`.
- Si `giro_id` se provee y el giro no pertenece al `sector_id` indicado: error 422 `giro_sector_mismatch`.
- Si se cambia `sector_id` sin proveer `giro_id`: `giro_id` se limpia a NULL automáticamente.

---

## Extensión al portal del proveedor

### `GET /portal/compliance` — respuesta extendida

```json
{
  "supplier_id": 42,
  "legal_name": "Constructora XYZ SA de CV",
  "sector": { "id": 1, "name": "Construcción" },
  "giro":   { "id": 3, "name": "Obra civil" },
  "cells": [...]
}
```

Si el proveedor no tiene clasificación: `"sector": null, "giro": null`.

El proveedor no puede modificar estos campos desde el portal (solo lectura).
