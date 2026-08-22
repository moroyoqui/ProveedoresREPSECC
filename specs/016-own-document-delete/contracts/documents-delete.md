# Contrato: Borrado de documentos en el back-office

**Feature**: 016-own-document-delete | **Base**: `/api/v1`

Este contrato modifica dos superficies existentes. No introduce endpoints nuevos.

---

## 1. `DELETE /documents/{document_id}`

Elimina un documento del back-office. **Cambio**: antes exigía rol `admin`; ahora admite además al `manager` **autor de la carga**.

### Autenticación y autorización

Sesión activa obligatoria. Roles admitidos en la ruta: `admin`, `manager`.

| Rol del solicitante | Documento propio | Documento ajeno |
|---|---|---|
| `admin` | permitido | permitido |
| `manager` | permitido | `403` |
| `viewer` | `403` | `403` |
| `supplier` | `403` (usa el endpoint del portal) | `403` |

### Petición

```
DELETE /api/v1/documents/{document_id}
```

Sin cuerpo. `document_id` es entero.

### Respuestas

Todas las respuestas de error usan el sobre estándar del proyecto:
`{"error": {"code": ..., "message": ..., "details": {...}}}`. El código fino
viaja en `error.details.code`.

| Código | Cuándo | `error.code` | `error.details.code` |
|---|---|---|---|
| `204` | Borrado ejecutado | — | — |
| `403` | Rol no admitido (`viewer`, `supplier`) | `forbidden` | — |
| `403` | `manager` sobre documento ajeno | `forbidden` | `not_document_owner` |
| `404` | No existe, ya borrado, o de otra organización | `not_found` | — |
| `409` | Documento verificado | `conflict` | `document_verified` |
| `409` | Celda enviada a validación o ya validada | `conflict` | `delete_not_allowed` |
| `409` | Fuera de la ventana de corrección | `conflict` | `delete_window_expired` (+ `grace_hours`) |
| `401` | Sin sesión | `unauthenticated` | — |

**Regla de precedencia**: existencia/tenant (404) → autoría (403) → verificado (409) → celda bloqueada (409) → ventana (409). Un tenant ajeno recibe `404`, nunca `403`.

### Efectos

- `deleted_at` se fija y `is_latest` pasa a `false`.
- La versión previa del mismo `(supplier, tipo, período)`, si existe, se promueve a vigente.
- El archivo físico se elimina del disco.
- Se escribe un evento de auditoría `document.deleted` con el actor y la marca temporal.
- Se invalida la caché del tablero del tenant.
- Los tokens de descarga emitidos antes dejan de resolver el archivo.

### Idempotencia

Un segundo `DELETE` sobre el mismo id responde `404`. El cliente trata `404` tras un borrado propio como éxito silencioso, no como error visible (edge case de doble clic).

---

## 2. `DocumentOut` — campo nuevo `can_delete`

Afecta a `GET /documents`, `GET /documents/{id}` y a las respuestas que devuelven un documento serializado.

```diff
 {
   "id": 123,
   "supplier_id": 45,
   "verified": false,
   "version": 2,
   "is_latest": true,
+  "can_delete": true,
   "file": { ... },
   "audit": {
     "added": { "user": { "id": 7, "display_name": "..." }, "at": "..." },
     ...
   }
 }
```

| Campo | Tipo | Semántica |
|---|---|---|
| `can_delete` | `boolean` | El usuario **de esta petición** puede intentar borrar este documento. Gobierna la visibilidad del botón. |

`can_delete = true` no garantiza un `204`: el estado de la celda se evalúa sólo al ejecutar el borrado, por lo que una celda bloqueada produce `409` con el botón visible (decisión de rendimiento documentada en el plan). El cliente debe manejar ese `409` mostrando el motivo.

**Compatibilidad**: campo aditivo. Los clientes que lo ignoren siguen funcionando; el frontend sin actualizar simplemente no muestra el botón.

---

## 3. Sin cambios: `DELETE /portal/documents/{document_id}`

El borrado del proveedor mantiene su contrato actual. La única alteración es interna: la comprobación de estado de celda pasa a invocarse desde `compliance/cell_locks.py` en lugar de una función local. Los tests existentes del portal deben seguir pasando sin modificarse — es el criterio de aceptación de ese refactor.
