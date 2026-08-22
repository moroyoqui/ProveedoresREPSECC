# Data Model: Unificación de "Validado" y "Verificado"

**Feature**: 017-unify-verification | **Fecha**: 2026-08-21

## Resumen

**Sin cambios de esquema**: ninguna columna nueva, ninguna tabla nueva, ningún renombrado. Lo que cambia es **de dónde sale la verdad**: una tabla deja de ser fuente de verdad y un campo derivado ocupa su lugar. Hay **una migración de datos** (no de estructura).

---

## Antes y después

```
ANTES — dos verdades que pueden contradecirse

  documents.verified ──────────► badge de /documents
                                 (autoría, fecha, nota, auditoría, reverso)

  compliance_cell_validations ──► estado de la rejilla
                                 (autoría, fecha; sin nota, sin auditoría, sin reverso)


DESPUÉS — una sola verdad

  documents.verified ──┬───────► badge de /documents
                       └───────► estado de la rejilla (derivado del documento vigente)

  compliance_cell_validations ──► (obsoleta; sin lectores ni escritores)
```

---

## Entidades

### Document — fuente de verdad única

Campos que pasan a gobernar también el estado de la celda:

| Campo | Papel |
|---|---|
| `verified` | **La marca única de revisión.** Antes sólo gobernaba `/documents`; ahora también la rejilla |
| `verified_by` | Autor de la revisión, venga de la pantalla que venga |
| `verified_at` | Fecha de la revisión |
| `verified_note` | Nota opcional; disponible ahora también al validar desde la rejilla (FR-012) |
| `is_latest` | Determina **qué documento** de la celda porta la marca — es único por celda (ver [research.md](research.md) R2) |
| `deleted_at` | Un documento borrado no porta marca; la celda se recalcula sobre la versión previa |

Sin cambios de columnas. El nombre técnico sigue siendo `verified` aunque la interfaz diga "Validado" (R8).

### Celda de cumplimiento — estado derivado

No es una tabla: es el cruce `(supplier_id, document_type_id, coverage_period_start)`.

```
type_validated  =  documento_vigente ≠ null  Y  documento_vigente.verified
```

`CellOut.type_validated` y `CellStatus.VALIDATED` **conservan nombre y semántica** de cara al cliente: el portal y la rejilla no notan el cambio de origen.

### ComplianceCellValidation — obsoleta

Deja de leerse y de escribirse. La tabla permanece en la base como red de seguridad de la migración (R7), marcada como obsoleta en el modelo. Una migración posterior la retirará.

### AuditEvent

Recibe ahora los eventos de la validación desde la rejilla, que antes no se auditaba en absoluto. Reutiliza las acciones existentes `document.verified` y `document.unverified`, sin códigos nuevos.

---

## Reglas de validación

| Regla | Origen | Respuesta al incumplirse |
|---|---|---|
| La celda tiene documento vigente para poder darse por revisada | FR-005 | `422 no_document_to_validate` |
| El rol es administrador o gestor, para marcar y para retirar | FR-007 | `403` |
| El proveedor no marca ni retira revisiones | FR-007 | `403` |
| El proveedor y la celda pertenecen al tenant del solicitante | Principio II | `404` |

---

## Transiciones de estado

**Del documento** (y por tanto de su celda):

```
sin revisar ──[validar desde la rejilla]──► revisado
            ──[verificar desde /documents]─►      │
                                                   │
revisado ────[retirar desde cualquiera de las dos]─┘──► sin revisar

revisado ────[se sube versión nueva]──► la versión nueva nace sin revisar
                                        y es la vigente ⇒ la celda vuelve
                                        a mostrarse pendiente (FR-009)

revisado ────[se borra el documento]──► la versión previa pasa a vigente
                                        y la celda hereda SU estado
```

Las dos primeras transiciones son **el mismo hecho** escrito desde dos pantallas: ahí está la unificación.

---

## Migración de datos

Recorre `compliance_cell_validations` **por organización**, sin cruzar tenants:

| Caso | Filas esperadas (medido en dev) | Acción |
|---|---|---|
| Celda con documento vigente sin verificar | 12 | Copiar `validated_by` → `verified_by`, `validated_at` → `verified_at`, `verified = true` |
| Celda con documento vigente ya verificado | incluido en los 12 | No pisar: se respeta la autoría del documento |
| Celda **sin documento vigente** | **32** | **Descartar**, registrando proveedor, tipo, período y fecha original en el log |
| Celda con documentos, todos borrados | 1 | Descartar, mismo registro |

Los **3 documentos verificados sin fila de validación** no necesitan nada: al derivar el estado, sus celdas pasan a mostrarse revisadas por sí solas.

**Irreversibilidad**: el descarte de las 32 filas no tiene vuelta atrás en cuanto a lo que muestra la rejilla —esas celdas volverán a "Faltante"—, aunque las filas originales sigan en la tabla obsoleta hasta su retirada definitiva.
