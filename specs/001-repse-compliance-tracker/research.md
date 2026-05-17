# Phase 0 Research: Bóveda de Cumplimiento REPSE (Core)

Este documento resuelve los unknowns del [plan.md](./plan.md) y deja registro de las decisiones técnicas + alternativas evaluadas para que un revisor pueda entender (y, si hace falta, revertir) cualquier elección.

---

## 1. Proveedores OAuth/OIDC para autenticación

**Decisión**: Soportar **Google** y **Microsoft (Azure AD / Entra ID)** desde v1 mediante OIDC con la librería `Authlib`. Sin contraseñas locales.

**Rationale**:
- Google y Microsoft cubren ≥95% de las cuentas corporativas en el mercado B2B mexicano.
- Authlib soporta OIDC genérico, ya integra ambos proveedores y se mantiene activamente.
- Elimina por completo el código de manejo de contraseñas (reset, rotación, lockout) → menor superficie de ataque.
- Compatible con el principio I de la constitución ("Secure by Default").

**Implementación**:
- Endpoints `/auth/login/{provider}` y `/auth/callback/{provider}`.
- Tras login se emite cookie `Set-Cookie: session=...; HttpOnly; Secure; SameSite=Lax; Path=/`.
- La sesión guarda `user_id`, `organization_id`, `role`, `expires_at` firmados con clave en disco (`itsdangerous`).
- Al primer login de un correo no registrado, si el dominio pertenece a una organización existente se ofrece "solicitar acceso" al admin; si no, se ofrece "crear nueva organización" (queda gated por verificación manual del primer admin en v1).

**Alternativas consideradas**:
- **Email + password local con argon2**: el spec FR-002 lo proponía. Rechazado: mayor superficie de ataque, mayor mantenimiento, peor UX para empresas con SSO ya en uso.
- **Auth0 / Clerk / Cognito**: violan el requisito on-prem (dependencia a SaaS externo).
- **Solo Google**: subestima el mercado mexicano donde Microsoft 365 domina.

---

## 2. ORM y migraciones

**Decisión**: SQLAlchemy 2.x con `Mapped`/`mapped_column` (ORM moderno) + Alembic para migraciones reversibles.

**Rationale**:
- SQLAlchemy es estándar de facto en Python; documentación robusta; tipado estricto en 2.x.
- Alembic produce migraciones reversibles (la constitución exige migraciones reversibles o con plan de forward-fix documentado).

**Patrón clave (multi-tenant)**:
- Mixin `TenantOwned` declara columna `organization_id: Mapped[int]` NOT NULL + relación a `Organization`.
- Event listener `before_compile` agrega filtro `where(Model.organization_id == current_tenant.id)` para cada Select que toque tablas con el mixin, **a menos** que se use el contexto `with_admin_scope()` (uso explícito para admin interno).
- Test de regresión: intentar borrar el filtro o usar `Session.execute(text("..."))` directo es bloqueado por code review + lint regla custom.

**Alternativas**:
- **Tortoise ORM / SQLModel**: menos maduros para casos multi-tenant complejos; integraciones de migración menos versátiles.
- **Raw SQL**: viola simplicidad de mantenimiento, abre la puerta a olvidar el filtro de tenant.

---

## 3. Cálculo de fecha de vencimiento (FR-009 del spec)

**Decisión**: implementar `expiration.compute_due_date(coverage_period: date, periodicity: Periodicity) -> date | None` en `documents/expiration.py` con las reglas:

```python
match periodicity:
    case MENSUAL:    # último día del mes siguiente a coverage_period
        return last_day_of_next_month(coverage_period)
    case BIMESTRAL:  # último día del bimestre fiscal SAT/IMSS siguiente
        return last_day_of_next_sat_imss_bimester(coverage_period)
    case ANUAL:      # último día del año fiscal siguiente
        return date(coverage_period.year + 1, 12, 31)
    case SIN_VIGENCIA:
        return None
```

**Bimestres oficiales SAT/IMSS** hardcodeados: `(1,2), (3,4), (5,6), (7,8), (9,10), (11,12)`.

**Override manual**: `Document.due_date_effective` (nullable) que prevalece sobre `due_date_calculated`. Cualquier escritura de `due_date_effective` distinta a `due_date_calculated` se anota en `AuditLog`.

**Alternativas**:
- Tabla de calendario oficial con prórrogas: rechazado para v1 (alta mantenibilidad); se permite override manual para los casos atípicos (días inhábiles, prórrogas SAT).

---

## 4. OCR (best-effort) sobre PDFs cargados

**Decisión**: `pytesseract` ≥0.3.10 + `pdf2image` para convertir PDFs a imágenes página por página (poppler como dep nativa del contenedor) + `tesseract-ocr-spa` y `tesseract-ocr-eng` instalados en la imagen Docker. Reglas regex sobre el texto extraído para detectar:

- **RFC del proveedor**: regex `[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}`.
- **Fecha de emisión / vigencia**: regex `\b(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})\b` con normalización a `date`.

**Modo de ejecución**:
1. Sincrónico si el PDF tiene ≤3 páginas (la mayoría de las opiniones SAT/IMSS).
2. Asíncrono via `BackgroundTasks` de FastAPI si excede 3 páginas; la respuesta de subida regresa `document.ocr_status = "pending"` y el front sondea cada 2 s hasta `success | failed`.

**Nunca bloquea la carga**: si OCR falla, `document.ocr_extracted = {}` y el flujo continúa.

**Alternativas**:
- **AWS Textract / Google Document AI**: violan el requisito on-prem y agregan costo por página.
- **PaddleOCR**: mejor precisión en español, requiere GPU para rendimiento decente; YAGNI en v1.

---

## 5. Almacenamiento de archivos local + descarga firmada

**Decisión**: `FileStore` con backend `LocalDisk(root="/var/repse/uploads")`. La descarga se sirve por un endpoint FastAPI `GET /files/{token}` donde `{token}` es un JWS firmado con `itsdangerous` que codifica `{file_id, user_id, organization_id, exp}` con TTL de 5 minutos. El endpoint:

1. Valida la firma.
2. Confirma `current_user.organization_id == token.organization_id`.
3. Sirve el archivo con `StreamingResponse` y headers `Content-Disposition`.

**Rationale**: cumple FR-019 del spec (acceso requiere sesión válida) sin exponer rutas de filesystem; los tokens caducan rápido para limitar reuso.

**Layout en disco**:
```
/var/repse/uploads/
└── {organization_id}/
    └── {supplier_id}/
        └── {document_id}/
            └── v{version}.{ext}
```

Permisos `0700` en directorios, `0640` en archivos; usuario propietario = el del proceso `app`.

**Backups**: `tar czf uploads-YYYYMMDD.tar.gz /var/repse/uploads/` diario en `var/backups/`. Restauración documentada en [quickstart.md](./quickstart.md).

**Alternativas**:
- MinIO embebido: introduce un servicio extra para el operador on-prem sin beneficio claro hasta multi-nodo.
- Servir directamente desde Caddy con `file_server` y X-Accel-Redirect: agrega complejidad de configuración; el throughput necesario (decenas de MB/s) no lo justifica.

---

## 6. Reverse proxy y TLS

**Decisión**: **Caddy** (no nginx).

**Rationale**:
- Configuración declarativa muy corta (Caddyfile).
- TLS automático con ACME (Let's Encrypt o ZeroSSL) en dominios públicos.
- Para entornos on-prem sin DNS público, soporta `tls internal` que genera cert autofirmado confiable dentro de la organización.
- Buen comportamiento por defecto (HTTP/2, gzip, security headers).

**Alternativas**:
- nginx: más control granular pero más fricción para casos simples; sin TLS automático nativo.
- Traefik: bueno para clusters dinámicos (k8s), overkill aquí.

---

## 7. Logging, métricas y errores

**Decisiones**:
- **Logs**: `structlog` con renderer JSON, sale a stdout. Operador on-prem rota con `logrotate` o agrega a su SIEM.
- Cada request agrega `request_id` (uuid4) + `tenant_id` + `user_id` al contexto.
- **Métricas**: endpoint `/metrics` con `prometheus_client` exponiendo request count, latency histogram, error rate, status calculation count, OCR success/failure. Operador puede scrape con Prometheus si lo desea (opcional).
- **Errores**: `sentry-sdk` configurable para apuntar a una instancia self-hosted de **GlitchTip** (compatible con el protocolo Sentry). Si la org no quiere correr GlitchTip, deja la variable `SENTRY_DSN` vacía y los errores quedan solo en logs.

**Asserción de privacidad**: helpers `redact_pii(obj)` ofuscan correos, RFCs y nombres antes de que vayan al backend de errores. Test unitario en CI verifica que ningún serializer expone `password`, `token`, `session`.

---

## 8. Rate limiting

**Decisión**: `slowapi` con backend en memoria por defecto (suficiente para una instancia). Reglas iniciales:

- `POST /auth/callback/*`: 10 / minuto / IP.
- `POST /documents`: 60 / minuto / usuario.
- Endpoints públicos (`/health`, `/metrics`): sin límite, pero los expone solo en localhost por defecto.

Si en producción se necesita multi-réplica, se cambia el storage a Redis. Decisión diferida hasta que aplique.

---

## 9. Catálogo canónico precargado

**Decisión**: definir el catálogo como datos sembrados (Python módulo `repse/catalog/canonical.py`) con tuplas `(slug, nombre, descripcion, periodicidad)`. Se aplica vía migration Alembic data-only (`op.bulk_insert`). Versión inicial:

| slug | Nombre | Periodicidad |
|------|--------|--------------|
| opinion-sat | Opinión de cumplimiento SAT (32-D) | mensual |
| opinion-imss | Opinión de cumplimiento IMSS | mensual |
| opinion-infonavit | Opinión de cumplimiento INFONAVIT | mensual |
| icsoe | ICSOE (Información de Contratos de Servicios) | cuatrimestral → modelado como bimestral por restricción del modelo de datos (clarificación pendiente) |
| sisub | SISUB (Sistema de Subcontratación) | cuatrimestral → idem |
| contrato-servicios | Contrato de servicios | sin vigencia |
| pago-cuotas-imss | Comprobantes de pago de cuotas IMSS | mensual |
| pago-cuotas-infonavit | Comprobantes de pago de cuotas INFONAVIT | bimestral (SAT/IMSS) |
| cfdi-nomina | CFDI de nómina | mensual |
| acta-constitutiva | Acta constitutiva del proveedor | sin vigencia |

**Aclaración pendiente**: ICSOE y SISUB son **cuatrimestrales** legalmente, no bimestrales. El modelo de datos del spec 001 contempla solo {mensual, bimestral, anual, sin vigencia}. Opciones para resolverlo:
1. Modelar como personalizado del tenant con periodicidad `bimestral` y override manual de vencimiento en cada carga (workaround).
2. Extender el modelo para soportar `cuatrimestral` (cambio de schema + migration + UI).

**Recomendación**: extender el modelo en una migration menor antes del lanzamiento. Lo dejo registrado como decisión a confirmar con el usuario (no bloquea el resto del plan).

---

## 10. Pruebas E2E

**Decisión**: Playwright (TypeScript) ejecutándose en CI contra un stack levantado con `docker compose -f ops/docker-compose.test.yml up`. Smoke tests por historia:

- US1: registrar tenant → login OAuth (mock) → crear proveedor → subir PDF de opinión SAT → ver documento en la lista con estado "Vigente".
- US2: tenant con datos sembrados → abrir detalle de proveedor → estados correctos → indicador agregado correcto.
- Multi-tenant negativo: usuario de Org A intenta `GET /suppliers/{id_de_org_B}` → 404.

**Alternativa**: Cypress. Rechazado porque Playwright es más rápido en CI, ofrece tracing y multi-browser sin configuración extra.

---

## Resumen de unknowns resueltos

| Tema | Decisión | Sección |
|------|----------|---------|
| Proveedores OAuth | Google + Microsoft | §1 |
| ORM y migraciones | SQLAlchemy 2.x + Alembic + mixin TenantOwned | §2 |
| Cálculo de vencimiento | Función `compute_due_date` por periodicidad | §3 |
| OCR | Tesseract local con pdf2image, best-effort | §4 |
| Almacenamiento | Disco local con FileStore + tokens firmados 5 min | §5 |
| Reverse proxy / TLS | Caddy con tls internal o ACME | §6 |
| Observabilidad | structlog JSON + Prometheus + GlitchTip opcional | §7 |
| Rate limiting | slowapi en memoria | §8 |
| Catálogo canónico | Seed en Python aplicado por migration Alembic | §9 |
| E2E | Playwright | §10 |

**Pendientes (no bloqueantes)**: definir manejo de ICSOE/SISUB cuatrimestrales (§9 sub-punto). Se confirma con el usuario antes de `/speckit-tasks`.
