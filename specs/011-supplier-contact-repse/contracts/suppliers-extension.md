# API Contract: Extensión del catálogo de proveedores

**Feature**: 011-supplier-contact-repse  
**Base path**: `/api/v1/suppliers`

---

## Campos nuevos / corregidos

Esta feature no añade endpoints nuevos. Extiende las respuestas y payloads de endpoints existentes.

### Campos añadidos a respuestas

| Endpoint | Campo | Tipo | Descripción |
|----------|-------|------|-------------|
| `GET /suppliers/{id}` | `contact_name` | `string \| null` | Nombre del contacto (antes omitido en detalle) |
| `GET /suppliers/{id}` | `contact_email` | `string \| null` | Correo del contacto (antes omitido en detalle) |
| `GET /suppliers/{id}` | `contact_phone` | `string \| null` | Teléfono del contacto (antes omitido en detalle) |
| `GET /suppliers/{id}` | `repse_folio` | `string \| null` | Folio de registro REPSE |
| `PATCH /suppliers/{id}` | `repse_folio` | `string \| null` | ídem en respuesta |
| `GET /portal/compliance` | `repse_folio` | `string \| null` | Folio REPSE del proveedor autenticado |

### Campos añadidos a payloads de escritura

| Endpoint | Campo | Tipo | Validación |
|----------|-------|------|-----------|
| `POST /suppliers` | `repse_folio` | `string \| null` | max_length=60, opcional |
| `PATCH /suppliers/{id}` | `repse_folio` | `string \| null` | max_length=60, opcional |

---

## `GET /suppliers/{id}` — Respuesta extendida

```json
{
  "id": 42,
  "legal_name": "Servicios Industriales del Norte SA de CV",
  "rfc": "SIN123456X1Z",
  "supplier_type": { "id": 1, "name": "Servicios Especializados", "origin": "system" },
  "sector": { "id": 3, "name": "Construcción" },
  "giro": { "id": 7, "name": "Obra civil" },
  "contact_name": "Juan Pérez López",
  "contact_email": "juan@serviciosindustriales.mx",
  "contact_phone": "+52 81 1234 5678",
  "repse_folio": "REPSE-2024-00001234",
  "status": "active",
  "compliance_percent": 85,
  "counts": { "valid": 6, "expiring_soon": 1, "expired": 0, "missing": 2 },
  "documents_by_type": [...],
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

## `PATCH /suppliers/{id}` — Payload extendido

```json
{
  "contact_name": "María García",
  "repse_folio": "REPSE-2024-00005678"
}
```

Respuesta: igual que `GET /suppliers/{id}` extendido.

---

## `GET /portal/compliance` — Respuesta extendida

```json
{
  "supplier": {
    "id": 42,
    "legal_name": "Servicios Industriales del Norte SA de CV",
    "rfc": "SIN123456X1Z",
    "supplier_type": { "id": 1, "name": "Servicios Especializados" },
    "status": "active",
    "compliance_percent": 85
  },
  "year": 2026,
  "sector": { "id": 3, "name": "Construcción" },
  "giro": { "id": 7, "name": "Obra civil" },
  "repse_folio": "REPSE-2024-00001234",
  "monthly_requirements": [...],
  "one_time_requirements": [...]
}
```

---

## Errores

| Código HTTP | `error.code` | Causa |
|-------------|-------------|-------|
| 422 | `validation_error` | `repse_folio` excede 60 caracteres |
| 422 | `validation_error` | `contact_name` excede 120 caracteres |

No hay nuevos códigos de error específicos de esta feature.
