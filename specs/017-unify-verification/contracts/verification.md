# Contrato: Revisión unificada de evidencia

**Feature**: 017-unify-verification | **Base**: `/api/v1`

Cuatro superficies afectadas. La regla que las gobierna a todas: **marcar o retirar la revisión escribe siempre en el documento vigente de la celda**, sea cual sea el endpoint por el que se entre.

Errores en el sobre estándar: `{"error": {"code": ..., "message": ..., "details": {...}}}`.

---

## 1. `POST /suppliers/{supplier_id}/compliance/validate` — cambia de semántica

Antes insertaba una fila en `compliance_cell_validations`. Ahora **verifica el documento vigente** de la celda.

### Petición

```json
{
  "document_type_id": 14,
  "coverage_period_start": "2026-07-01",
  "note": "Cotejado con el portal del SAT"
}
```

`coverage_period_start` es `null` para tipos sin periodicidad. `note` es **nuevo** y opcional (FR-012).

### Respuestas

| Código | Cuándo | `error.details.code` |
|---|---|---|
| `200` | Documento vigente marcado como revisado | — |
| `403` | Rol distinto de administrador o gestor | — |
| `404` | Proveedor inexistente o de otra organización | — |
| `422` | **La celda no tiene documento vigente** (FR-005) | `no_document_to_validate` |

```json
{ "status": "validated", "validated_at": "...", "document_id": 56 }
```

`document_id` es **nuevo**: identifica qué documento porta ahora la marca.

### Cambios de comportamiento a señalar

- **Ya no se puede validar una celda vacía.** Antes se permitía y era la causa de las 32 marcas huérfanas.
- **Ahora queda auditado** (`document.verified`), cuando antes no dejaba rastro alguno.

---

## 2. `POST /suppliers/{supplier_id}/compliance/unvalidate` — nuevo

Retira la revisión del documento vigente de la celda. No existía equivalente: la validación de celda era irreversible.

Mismo cuerpo que `validate` (sin `note`). Roles: administrador y gestor.

| Código | Cuándo | `error.details.code` |
|---|---|---|
| `200` | Revisión retirada | — |
| `403` | Rol no admitido | — |
| `404` | Proveedor inexistente o de otra organización | — |
| `422` | La celda no tiene documento vigente | `no_document_to_validate` |

**Idempotente**: retirar la revisión de una celda que no estaba revisada responde `200` sin efecto, reutilizando el comportamiento que `unverify_document()` ya tenía. No se introduce un `409` nuevo para un caso que el servicio resuelve sin error.

---

## 3. `POST /documents/{id}/unverify` — cambia de permiso

| | Antes | Ahora |
|---|---|---|
| Roles | `admin` | `admin`, `manager` |

Es la única relajación de control de la feature (FR-007), decidida explícitamente. `POST /documents/{id}/verify` no cambia.

**Efecto nuevo**: retirar la verificación desde `/documents` hace que la celda deje de figurar revisada en la rejilla, de forma inmediata.

---

## 4. Rejilla de cumplimiento — mismo contrato, otro origen

`GET /suppliers/{id}/compliance` **no cambia de forma**. `CellOut.type_validated` y `CellStatus.VALIDATED` conservan nombre y significado; lo que cambia es de dónde salen:

```diff
- type_validated = existe fila en compliance_cell_validations
+ type_validated = documento vigente de la celda && documento.verified
```

**Compatibilidad**: total para el cliente. El portal del proveedor no requiere cambio alguno.

**Cambios observables** para el usuario, derivados del origen nuevo:

1. Una celda cuyo documento se verificó desde `/documents` ahora aparece validada en la rejilla (antes no).
2. Subir una versión nueva sobre una celda validada la devuelve a pendiente (antes seguía diciendo "Validado" sobre evidencia sin revisar).
3. Las 32 celdas validadas sin documento vuelven a mostrarse como "Faltante".

---

## 5. `DELETE /documents/{id}` (feature 016) — se simplifica

Los dos motivos de rechazo por revisión eran en realidad el mismo. Tras la unificación:

| Motivo de rechazo | Antes | Ahora |
|---|---|---|
| Documento verificado | `document_verified` | `document_verified` |
| Celda validada | `delete_not_allowed` | *(colapsado en el anterior)* |
| Envío del proveedor pendiente | `delete_not_allowed` | `delete_not_allowed` |

`delete_not_allowed` queda reservado al envío pendiente del portal. El proveedor no percibe cambio: las dos condiciones que antes le bloqueaban el borrado ahora son una sola con el mismo efecto.
