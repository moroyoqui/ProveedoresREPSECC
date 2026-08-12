# Quickstart — 013 Portal Upload Separation

## Qué hace esta feature

Separa por completo la experiencia del proveedor de la del back-office:

1. **Login dedicado** `/portal/login` (solo email+password) con gating por audiencia en `POST /auth/login` (campo nuevo `audience`).
2. **Dos pantallas** bajo un layout propio `PortalShell`: `/portal/consulta` (solo lectura) y `/portal/carga` (upload + enviar a validar). `/portal` redirige a consulta.
3. **Servicios segregados**: `repse/portal/routes.py` se divide en `routes_read.py` (3 GET, cero escrituras) y `routes_write.py` (2 POST), mismas URLs.

Sin migraciones de BD; sin cambios en `SessionPayload` ni en reglas de negocio de 009.

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

1. Crear (como admin en `/users`) un usuario rol proveedor vinculado a una empresa.
2. Abrir `/portal/login`, entrar con esa cuenta → debe aterrizar en `/portal/consulta` con menú de solo dos opciones + cerrar sesión.
3. Verificar que `/portal/consulta` no tiene ningún botón de carga ni "Enviar a validar".
4. Desde una celda Faltante/Vencido usar "Ir a cargar" → `/portal/carga` con tipo y período preseleccionados; subir archivo y enviar a validar; volver a consulta → estado "Pendiente de validación" visible sin recargar.
5. Intentar entrar con la cuenta proveedor en `/login` (back-office) → mismo mensaje de "Correo o contraseña incorrectos" + enlace estático al portal.
6. Con sesión admin, navegar a `/portal/consulta` → redirect al área administrativa.

## Tests

```bash
cd backend
pytest tests/test_auth_entry.py tests/test_portal_auth.py tests/test_portal_isolation.py tests/test_portal_read_only.py -q
```

- `test_auth_entry.py` (nuevo): audiencia cruzada → respuesta idéntica a `invalid_credentials`; audiencia correcta → 200.
- `test_portal_read_only.py` (nuevo): endpoints de `routes_read` solo GET y sin escrituras; supplier recibe 403 en endpoints administrativos (SC-003/SC-004).
- Suites de 009 deben seguir en verde sin modificación de lógica (FR-007, SC-005).

## Deuda anotada (fuera de alcance v1)

- El callback OIDC no aplica gating de audiencia: una cuenta supplier que entre por Google/Microsoft en `/login` obtiene sesión y es redirigida al portal por rol (Decision 4 de research.md).
