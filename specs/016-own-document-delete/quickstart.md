# Quickstart — 016 Borrado de Documentos Propios

## Qué hace esta feature

Da a quien carga documentos en el back-office la capacidad de corregir sus propias cargas equivocadas, sin escalar a un administrador:

1. **Permiso ampliado** en `DELETE /documents/{id}`: antes sólo `admin`, ahora también el `manager` **autor** de la carga. La regla vive en `service.delete_document()`, no sólo en la ruta.
2. **Campo nuevo `can_delete`** en `DocumentOut`, calculado por el servidor (autoría + rol + verificado + ventana de gracia). Gobierna la visibilidad del botón.
3. **Botón "Eliminar"** en el footer del drawer de detalle, con `DestructiveConfirmDialog` que nombra proveedor, tipo y período.
4. **Refactor menor**: `_check_delete_allowed` sale de `portal/routes_write.py` a `compliance/cell_locks.py` como `check_cell_unlocked()`, para que ambos canales compartan la regla.

Sin migraciones de BD. Sin cambios de comportamiento en el portal del proveedor.

## Desarrollo local

```bash
# Backend
cd backend
uvicorn repse.main:app --reload    # http://localhost:8000

# Frontend
cd frontend
npm run dev                        # http://localhost:5173
```

## Verificación manual rápida

1. Entrar como **gestor** (`manager`) y subir un documento a cualquier proveedor.
2. Abrir ese documento desde `/documents` → el drawer muestra el botón **Eliminar**.
3. Pulsarlo → el diálogo nombra proveedor, tipo de documento y período, y advierte que la acción es irreversible. **Cancelar** → el documento sigue ahí, intacto.
4. Repetir y **confirmar** → el documento desaparece del listado sin recargar, y la celda de cumplimiento del proveedor vuelve a su estado previo (o a la versión anterior, si existía).
5. Entrar como **otro gestor** y abrir un documento del primero → **no** hay botón Eliminar.
6. Entrar como **consultor** (`viewer`) → no hay botón Eliminar en ningún documento.
7. Entrar como **admin** → botón visible sobre cualquier documento (comportamiento previo, conservado).
8. Como admin, verificar un documento y volver a mirarlo como su autor → el botón desaparece (hay que quitar la verificación primero).
9. Consultar el historial de la celda tras un borrado → aparece "Eliminó el documento" con autor y fecha.

**Caso de borde a comprobar**: un documento cuya celda el proveedor ya envió a validación muestra el botón, pero al confirmar responde con el motivo del rechazo en lugar de borrar. Es la consecuencia asumida de no consultar el estado de celda por fila en el listado.

## Tests

```bash
# Backend — desde la raíz del repo, con backend/.venv activo y Docker corriendo
pytest backend/tests/contract/test_documents_delete_contract.py -q
pytest backend/tests/integration/test_tenant_isolation.py -q

# Regresión del portal: debe pasar sin modificar ningún test
pytest backend/tests/test_portal_upload.py backend/tests/test_portal_isolation.py -q

# Frontend
cd frontend && npm run test
```

## Qué revisar en code review

- La verificación de autoría está **dentro** de `service.delete_document()`, no sólo en la ruta (Principio I).
- Existe el test negativo de cruce entre organizaciones y devuelve **404**, no 403 (Principio II).
- `check_cell_unlocked()` se invoca **desde las rutas**, no desde el servicio compartido — es la convención declarada en `portal/routes_write.py:1-14`.
- El cálculo de `can_delete` en el listado no dispara una consulta por fila.
