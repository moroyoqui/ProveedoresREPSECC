# Data Model: Mejoras UX tabla de usuarios (015)

> Esta feature es puramente de presentación. No se agregan ni modifican entidades en la base de datos ni en el backend.

## Tipo existente reutilizado: `UserItem`

Fuente: `frontend/src/lib/api/index.ts`

| Campo | Tipo | Usado en panel de detalle |
|-------|------|--------------------------|
| `id` | `number` | No (clave interna) |
| `email` | `string` | Sí |
| `display_name` | `string` | Sí |
| `role` | `"admin" \| "manager" \| "viewer" \| "supplier"` | Sí |
| `status` | `"active" \| "disabled"` | Sí |
| `supplier_id` | `number \| null` | No (solo como señal) |
| `supplier_name` | `string \| null` | Sí (si rol = supplier) |
| `last_login_at` | `string \| null` | No — eliminado de la tabla |

## Componentes nuevos / modificados

### `IconButton` (nuevo — `frontend/src/components/ui/Tooltip.tsx` o `IconButton.tsx`)

Props:
- `icon`: `React.ReactNode` — el ícono a renderizar
- `label`: `string` — texto del tooltip y `aria-label`
- `onClick?`: handler
- `disabled?`: boolean
- `variant?`: `"ghost" | "secondary"` (hereda de `Button`)

Renderizado:
```
<div class="relative group inline-flex">
  <button aria-label={label} ...>{icon}</button>
  <span role="tooltip" class="absolute ... invisible group-hover:visible">
    {label}
  </span>
</div>
```

### `UserDetailDrawer` (componente interno de `list.tsx`)

Props:
- `user: UserItem`
- `onClose: () => void`

Campos mostrados (solo lectura):
- Nombre (`display_name`)
- Correo (`email`)
- Rol (etiqueta en español via `ROLE_LABEL`)
- Estado (badge activo/deshabilitado)
- Proveedor (`supplier_name` si rol = "supplier", "—" si no aplica)
