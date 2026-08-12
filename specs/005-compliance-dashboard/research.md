# Research: Tablero de Control de Cumplimiento (005)

Fase 0. Resuelve las decisiones técnicas abiertas del spec. Todas las "NEEDS CLARIFICATION" del Technical Context quedan cerradas abajo.

---

## Decisión 1 — Librería de gráficos (pastel + barras)

- **Decisión**: Usar **Recharts** (`recharts`) como única dependencia nueva del frontend para el pastel y el gráfico de barras.
- **Rationale**: El stack ya es React 18 + Vite. Recharts es la opción más establecida y mejor soportada para gráficos declarativos en React, compone bien con Tailwind (colores por `fill`/`Cell`), soporta `onClick` por porción/barra (necesario para el drill-down FR-015/FR-016) y trae tooltips y leyendas accesibles de fábrica. Cumple "boring, well-supported" de la constitución (IV).
- **Alternativas consideradas**:
  - *SVG manual / `<svg>` a mano*: cero dependencias, pero reimplementar arcos del pastel, ejes del bar chart, tooltips, leyendas y accesibilidad es más código del que ahorra; viola la simplicidad por costo de mantenimiento.
  - *Chart.js (`react-chartjs-2`)*: basado en canvas, drill-down por click menos ergonómico y peor accesibilidad/branding con Tailwind que un árbol SVG.
  - *visx*: muy flexible pero de bajo nivel; exige construir cada primitiva, más complejidad de la requerida para dos gráficos simples.

## Decisión 2 — Agregación en servidor

- **Decisión**: Toda la agregación se hace en MySQL con consultas `GROUP BY` scoped por `organization_id`, dentro de `dashboard/service.py`. El cliente nunca recibe documentos fila por fila.
- **Rationale**: FR-020 y SC-001/SC-002 exigen agregación en servidor y tiempos < 2 s / < 1.5 s con hasta 50 000 documentos. Los índices existentes en `documents` (`ix_documents_org_supplier_type_period`, `ix_documents_org_status`, `ix_documents_org_due`) cubren los filtros por tenant/tipo/periodo/estado.
- **Forma del cálculo**:
  - El universo de "celdas requeridas" se deriva, igual que en el spec 006, de los `SupplierTypeDocumentRequirement` **activos** que apuntan a `DocumentType` **activos**, expandidos por periodicidad sobre el año filtrado. Cada celda requerida sin documento que cubra el periodo cuenta como **faltante**.
  - El estado de cada documento se calcula con `documents.status.compute_status(doc, today=ref_date, expiring_soon_threshold_days=...)`, reutilizando la misma función que el detalle por proveedor para garantizar SC-003.
- **Alternativas consideradas**: Calcular en cliente (rechazado por FR-020 y escala); materializar una tabla de snapshot (rechazado por YAGNI y por la exigencia de frescura casi-real).

## Decisión 3 — Semántica del año y fecha de referencia ("snapshot")

- **Decisión**: La fecha de referencia `ref_date` que se pasa a `compute_status` depende del año filtrado:
  - **Año en curso** → `ref_date = hoy` en zona horaria del tenant (FR-011).
  - **Año pasado** → `ref_date = 31-dic 23:59` del año seleccionado, en zona horaria del tenant (FR-012). Así "por vencer"/"vencido" reflejan el estado de cierre de ese año, no proyectado a hoy.
  - **Año futuro** → conjunto vacío / estado vacío (FR-005 limita el selector, pero el servicio lo maneja con seguridad).
- **Alcance del año**: documentos cuyo **periodo cubierto intersecta** el año (no la fecha de carga). Documentos "sin vigencia" (sin `coverage_period_start`) se incluyen solo si su fecha de carga cae en el año (FR-013).
- **Rationale**: `compute_status` ya recibe `today` como parámetro, así que el snapshot histórico no requiere lógica nueva, solo elegir la fecha de referencia correcta.
- **Alternativas consideradas**: Recalcular todo contra hoy siempre (rechazado: distorsiona auditorías retrospectivas, contradice FR-012).

## Decisión 4 — Cache en servidor (60 s) e invalidación

- **Decisión**: Cache **en proceso** (diccionario en memoria con TTL de 60 s) keyed por `(organization_id, filtros_normalizados)`. La invalidación se implementa con un **contador de versión por tenant**: la clave de cache incluye `version[organization_id]`; los eventos de FR-021a incrementan ese contador, lo que deja obsoletas todas las entradas del tenant sin necesidad de rastrear claves individuales.
- **Eventos que incrementan la versión** (FR-021a): carga/edición/eliminación de documento; activar/desactivar/archivar un tipo en el catálogo; alta/baja/reactivación de proveedor; cambio de configuración que afecte el cálculo de estado (umbral "por vencer", overrides de vencimiento).
- **Rationale**: El despliegue es on-prem single-backend (Docker Compose); un cache en proceso satisface FR-021 sin introducir Redis (YAGNI, constitución IV). El contador de versión evita el problema de invalidación selectiva y es O(1).
- **Indicador de frescura** (FR-021b): la respuesta incluye `calculated_at` (hora local del tenant) que el frontend muestra como "última actualización".
- **Alternativas consideradas**: Redis/memcached (rechazado: complejidad innecesaria para un solo proceso); invalidación por borrado explícito de claves (rechazado: frágil y verboso frente al contador de versión); sin cache (rechazado por FR-021 ante refrescos repetidos).

## Decisión 5 — Zona horaria del tenant

- **Decisión**: La zona horaria se toma de la organización (por defecto `America/Mexico_City`). "Hoy", los límites 1-ene/31-dic y el `calculated_at` se calculan en esa zona; el frontend rotula explícitamente la zona (FR-021b, edge case de huso horario).
- **Rationale**: El spec exige consistencia de zona horaria del tenant en todos los cortes temporales.
- **Alternativas consideradas**: UTC puro (rechazado: desplaza límites de año/día para usuarios en CDMX).

## Decisión 6 — Filtros en la URL y drill-down

- **Decisión**: Los filtros del tablero se codifican en `URLSearchParams` (`year`, `supplier_type`, `document_type`, `supplier`, `status`, `include_inactive`) vía `react-router-dom` `useSearchParams`. El drill-down navega al listado existente de documentos/proveedores propagando esos mismos parámetros + la dimensión seleccionada (estado del pastel, tipo de la barra, subconjunto del KPI).
- **Rationale**: FR-008 (recargar/compartir reconstruye la vista) y FR-009 ("limpiar filtros" = navegar a la URL base). Reutiliza el enrutado ya presente.
- **Alternativas consideradas**: Estado solo en memoria (rechazado por FR-008); persistir filtros en backend por usuario (fuera de alcance, YAGNI).

## Decisión 7 — Redondeo del pastel a 100% exacto (SC-007)

- **Decisión**: Calcular porcentajes con el método del **mayor residuo** (Hamilton): redondear cada porción hacia abajo, repartir las unidades restantes a las porciones con mayor parte fraccionaria hasta sumar 100. El servidor devuelve tanto conteos absolutos como porcentajes ya cuadrados a 100.
- **Rationale**: Evita el clásico "99% / 101%" del redondeo independiente; lo resuelve el servidor para que todos los clientes vean la misma cifra.
- **Alternativas consideradas**: Redondeo simple por porción (rechazado: viola SC-007); redondeo solo en cliente (rechazado: inconsistente entre vistas).

---

## Resumen de cierre

| Tema | Decisión |
|------|----------|
| Gráficos | Recharts |
| Agregación | `GROUP BY` en MySQL, scoped por tenant, reutiliza `compute_status` |
| Snapshot por año | `ref_date` = hoy (año en curso) / 31-dic del año (año pasado) |
| Cache | En proceso, TTL 60 s, invalidación por contador de versión por tenant |
| Zona horaria | Del tenant (default America/Mexico_City) |
| Filtros/drill-down | URLSearchParams + propagación al listado |
| Redondeo pastel | Mayor residuo (Hamilton) en servidor → 100% exacto |

Sin "NEEDS CLARIFICATION" pendientes.
