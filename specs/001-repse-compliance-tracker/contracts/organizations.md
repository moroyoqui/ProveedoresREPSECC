# Contract: Organizations

Lectura y configuración del tenant del usuario actual. No hay endpoints para listar otras orgs (eso es interno).

## GET `/api/v1/organization`

Devuelve la organización del usuario actual.

- **Auth**: requerida.
- **Roles**: cualquiera.
- **Respuesta** `200`:
  ```json
  {
    "id": 7,
    "legal_name": "Constructora REPSECC SA de CV",
    "rfc": "CRP120304XYZ",
    "contact_email": "compliance@repsecc.mx",
    "expiring_soon_threshold_days": 15,
    "timezone": "America/Mexico_City",
    "status": "active"
  }
  ```

## PATCH `/api/v1/organization`

Actualiza configuración del tenant.

- **Auth**: requerida.
- **Roles**: admin.
- **Body**:
  ```json
  {
    "legal_name": "Constructora REPSECC SA de CV",
    "contact_email": "compliance@repsecc.mx",
    "expiring_soon_threshold_days": 30,
    "timezone": "America/Mexico_City"
  }
  ```
  Todos los campos opcionales (PATCH parcial).
- **Validaciones**:
  - `expiring_soon_threshold_days`: 1..90.
  - `timezone`: zona IANA válida.
- **Respuesta** `200`: organización actualizada.
- **Side effects**: si cambia `expiring_soon_threshold_days`, dispara recálculo asíncrono del `status` de todos los documentos del tenant.
- **Errores**: `400 validation_error`, `403 forbidden`.

## Reglas de autorización

| Endpoint | viewer | manager | admin |
|----------|--------|---------|-------|
| GET /organization | ✅ | ✅ | ✅ |
| PATCH /organization | 403 | 403 | ✅ |
