# Research: Asignar Proveedor a Usuario

## Estado actual del código

### Decision: Backend ya implementado al 100%
- **Rationale**: `User.supplier_id` existe en BD con FK a `suppliers.id ON DELETE SET NULL`. `UserCreate` ya requiere `supplier_id` para rol supplier (validador Pydantic). `UserPatch` acepta `supplier_id`. `update_user` ya maneja reasignación y limpieza al cambiar de rol. `_validate_supplier_ownership` protege contra supplier de otra org.
- **Gap**: `UserOut` no expone `supplier_name` — solo `supplier_id`. La UI no puede mostrar el nombre sin join o lookup adicional.

### Decision: Frontend crear usuario ya implementado
- **Rationale**: `CreateUserDialog` en `frontend/src/pages/users/list.tsx` ya carga `suppliersApi.list({ status: "active" })` y muestra el selector cuando `role === "supplier"`.
- **Gap 1**: La tabla no tiene columna "Proveedor".
- **Gap 2**: Para usuarios supplier existentes no hay UI para cambiar/asignar el proveedor.
- **Gap 3**: El dropdown inline de rol (en la tabla) permite seleccionar "supplier" pero llama `usersApi.update(id, { role: "supplier" })` sin `supplier_id`, lo que produce un error 404 de la API si el usuario no tenía supplier_id previo.

## Decisiones de diseño

### Decision: Enriquecer UserOut con supplier_name en el backend
- **Rationale**: Más simple que cargar todos los proveedores en el frontend y hacer lookup. Un LEFT JOIN en `list_users` es trivial. Evita N+1 y no requiere estado adicional en el frontend.
- **Alternatives considered**: Cargar `suppliersApi.list()` siempre en la página de usuarios y mapear por id — más peticiones, más estado, más complejo.

### Decision: Añadir diálogo "Cambiar proveedor" para usuarios supplier existentes
- **Rationale**: Reutiliza el patrón ya establecido en la página (modales para acciones). Mínimo código nuevo.
- **Alternatives considered**: Editar inline en la tabla — más complejo, no necesario.

### Decision: Proteger dropdown inline contra selección de "supplier"
- **Rationale**: Cambiar a "supplier" via dropdown inline nunca puede funcionar sin `supplier_id`. Deshabilitar la opción "supplier" en el dropdown inline y mostrar un hint es más honesto que dejar que falle silenciosamente. El flujo correcto es: crear el usuario con supplier desde el inicio, o usar el diálogo "Cambiar proveedor".
- **Alternatives considered**: Interceptar el change event y abrir modal — más código, más confuso para el usuario.

## Sin investigación adicional necesaria
- No hay migraciones de BD requeridas.
- No hay cambios de API (solo enriquecimiento de `UserOut`).
- Toda la lógica de negocio ya existe en el backend.
