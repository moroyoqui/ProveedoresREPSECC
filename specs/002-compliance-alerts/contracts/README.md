# API Contracts: Alertas y Recordatorios

Endpoints específicos del spec 002. Convenciones globales (auth, errores, paginación, multi-tenant) heredan del [contracts/README del 001](../../001-repse-compliance-tracker/contracts/README.md).

| Archivo | Cobertura |
|---------|-----------|
| [alert-config.md](./alert-config.md) | Configuración por organización (antelación, destinatarios, horario) y sobrescritura por proveedor. |
| [alert-silences.md](./alert-silences.md) | Silenciamiento manual de alertas por documento. |
| [notifications.md](./notifications.md) | Listado, lectura y disparo manual de notificaciones in-app. |

## Tests de contrato (obligatorios por constitución)

Para cada endpoint:

1. **Forma de respuesta**: valida contra el esquema Pydantic generado.
2. **Auth required**: sin sesión retorna 401.
3. **Multi-tenant negativo**: con sesión de Org B contra recurso de Org A → 404.
4. **Rol insuficiente**: viewer intentando endpoints de admin → 403.
5. **Idempotencia diaria** (específico de este spec): el scheduler de un tenant invocado dos veces en el mismo día no crea filas duplicadas en `notifications` (constraint unique).
