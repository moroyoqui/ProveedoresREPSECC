# Quickstart — 017 Unificación de "Validado" y "Verificado"

## Qué hace esta feature

Convierte dos marcas de revisión que podían contradecirse en una sola:

1. **El documento manda**: `documents.verified` pasa a gobernar también el estado de la rejilla. La celda deriva su estado del documento vigente.
2. **Validar desde la rejilla = verificar el documento**: el endpoint de validar celda escribe ahora en el documento, exige que exista evidencia y queda auditado (antes no dejaba rastro).
3. **Aparece el reverso que faltaba**: `unvalidate` a nivel de celda, y `unverify` pasa a estar disponible también al gestor.
4. **Migración del histórico**: 12 validaciones se trasladan al documento; 32 sin evidencia se descartan dejando constancia.
5. **La interfaz dice "Validado"** en todas partes; la columna sigue llamándose `verified` internamente.

Sin cambios de esquema. El portal del proveedor no cambia de comportamiento.

## Desarrollo local

```bash
# Backend
cd backend
uvicorn repse.main:app --reload    # http://localhost:8000

# Frontend
cd frontend
npm run dev                        # http://localhost:5173

# O el stack completo
docker compose --env-file ops/.env -f ops/docker-compose.yml up -d   # http://localhost:9080
```

## Antes de migrar: fotografía del estado

```bash
docker compose --env-file ops/.env -f ops/docker-compose.yml exec -T mysql \
  mysql -u root -p'5i5tem@5' repse -e "
SELECT COUNT(*) AS validaciones FROM compliance_cell_validations;
SELECT COUNT(*) AS docs_verificados FROM documents WHERE verified=1 AND deleted_at IS NULL;"
```

Guarda esos números: la verificación posterior se apoya en ellos.

## Verificación manual

**Coherencia en ambos sentidos (US1)** — el fallo que originó la feature:

1. Como gestor, abre la rejilla de un proveedor y valida una celda **con documento**. Ve a `/documents` y comprueba que ese documento figura validado, con tu nombre y la fecha.
2. Al revés: valida un documento desde `/documents`, vuelve a la rejilla y comprueba que su celda aparece validada sin repetir la acción.
3. Intenta validar una celda **sin documento** → el sistema lo impide explicando que no hay evidencia que respaldar.

**El reverso (US2)**:

4. Retira la validación desde la rejilla → el documento deja de figurar validado en `/documents`.
5. Retira la validación desde `/documents` → la celda deja de figurar validada en la rejilla.
6. Como consultor (`viewer`), comprueba que no se te ofrece ninguna de las dos acciones.
7. Consulta el historial del documento: constan la validación y su retirada, con autor y fecha.

**Comportamiento nuevo que conviene ver funcionar**:

8. Sobre una celda validada, sube una versión nueva del documento → la celda vuelve a "Pendiente de validación". Antes seguía diciendo "Validado" sobre evidencia que nadie había mirado.

**Caso concreto reportado**:

9. Prov1 · Cédula cuota IMSS · julio 2026 (documento 56): tras la migración debe verse validado en `/documents`, coherente con su celda.

## Tests

```bash
# Backend — desde la raíz, con backend/.venv y Docker
pytest backend/tests/integration/test_verification_unification.py -q
pytest backend/tests/integration/test_migration_unify_validation.py -q

# Regresión: el portal y el borrado de 016 no deben cambiar de comportamiento
pytest backend/tests/test_portal_upload.py backend/tests/test_portal_isolation.py -q
pytest backend/tests/contract/test_documents_delete_contract.py -q

# Suite completa
pytest backend/tests -q
cd frontend && npm run test
```

## Después de migrar: comprobación

```bash
docker compose --env-file ops/.env -f ops/docker-compose.yml exec -T mysql \
  mysql -u root -p'5i5tem@5' repse -e "
-- Debe dar 0: ninguna celda con documento vigente queda sin alinear
SELECT COUNT(*) AS sin_alinear FROM compliance_cell_validations v
JOIN documents d ON d.supplier_id=v.supplier_id AND d.document_type_id=v.document_type_id
  AND (d.coverage_period_start <=> v.coverage_period_start)
  AND d.is_latest=1 AND d.deleted_at IS NULL
WHERE d.verified=0;"
```

## Qué revisar en code review

- La rejilla **no consulta** `compliance_cell_validations` en ningún camino (`grep` debe salir vacío fuera de la migración y del modelo).
- La migración itera **por organización** y no cruza tenants.
- La migración **registra** las filas que descarta antes de descartarlas.
- `CellStatus` y `CellOut.type_validated` conservan nombre y semántica: el portal no necesita cambios.
- `check_cell_unlocked` se queda sólo con el envío pendiente del portal.

## Aviso antes de desplegar

Las **32 celdas de Prov6 validadas sin documento volverán a mostrarse como "Faltante"**. Es la decisión tomada al planificar (validar sin evidencia deja de tener sentido), pero es un cambio visible: conviene avisar a quien use esa rejilla antes de desplegar.
