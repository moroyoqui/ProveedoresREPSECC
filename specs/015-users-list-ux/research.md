# Research: Mejoras UX tabla de usuarios (015)

## Decisión 1 — Implementación de Tooltips

**Decision**: Componente `IconButton` en `components/ui/` con tooltip via `group` de Tailwind + `absolute` positioning.

**Rationale**: El atributo nativo `title` no es estilizable y su delay es dependiente del OS. Un micro-componente con `relative group` de Tailwind CSS (ya en uso en el proyecto) produce un tooltip consistente con el design system sin agregar dependencias. Radix UI tiene `Tooltip` pero sería sobre-ingeniería para este caso.

**Alternatives considered**:
- `title` HTML nativo: descartado — no estilizable, delay no controlado.
- Radix UI `Tooltip`: descartado — dependencia nueva innecesaria cuando Tailwind puede resolverlo con < 20 líneas.

---

## Decisión 2 — Panel de detalle del usuario

**Decision**: Modal centrado (mismo patrón que `CreateUserDialog` y `ChangeSupplierDialog` ya en `list.tsx`).

**Rationale**: El proyecto ya tiene el patrón `fixed inset-0 z-40 flex items-center justify-center` en tres diálogos de la misma página. Reutilizarlo mantiene coherencia visual y evita introducir un drawer lateral (más complejidad de animación/accesibilidad).

**Alternatives considered**:
- Drawer lateral: descartado — requiere animación y manejo de foco más complejo; el modal es suficiente para un formulario de solo lectura con pocos campos.
- Página de detalle separada con navegación: descartado — rompe el flujo actual de la tabla; la spec indica que debe abrirse desde el nombre clicable sin salir de la pantalla.

---

## Decisión 3 — Campo `created_at`

**Decision**: Omitir del panel de detalle.

**Rationale**: El esquema `UserOut` del backend no expone `created_at`. Agregar ese campo al backend (modelo + schema + migración) quedaría fuera del alcance de esta feature. El panel mostrará: nombre, correo, rol, estado, y proveedor asignado.

**Alternatives considered**:
- Agregar `created_at` al backend: descartado — fuera del alcance definido en la spec (sin cambios en el backend).

---

## Decisión 4 — Responsividad de la tabla

**Decision**: Scroll horizontal en viewport < 768 px (ya resuelto con `overflow-x-auto` aplicado en esta misma rama en `Table.tsx`).

**Rationale**: Ya se corrigió `overflow-hidden` → `overflow-x-auto` en el componente `Table`. Con íconos compactos (sin texto) en la columna de acciones, la tabla cabrá en viewports medianos (≥ 900 px) sin scroll. En viewports < 768 px el scroll horizontal es la solución más simple y ya está activa.

**Alternatives considered**:
- Ocultar columnas secundarias en móvil con `hidden sm:table-cell`: posible mejora futura pero innecesaria dado que la tabla es de administración interna, no de uso móvil primario.
