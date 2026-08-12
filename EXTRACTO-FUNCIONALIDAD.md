# Extracto de Funcionalidad — Plataforma de Cumplimiento REPSE

> Documento de referencia funcional para elaborar una presentación de venta.
> Describe **qué hace** el producto (capacidades y valor), no cómo está construido.
> Producto SaaS multi-tenant para gestionar el cumplimiento de proveedores REPSE bajo la Ley Federal del Trabajo, Art. 15.

---

## ¿Qué problema resuelve?

Las empresas que contratan proveedores de servicios especializados (REPSE) tienen la obligación legal de comprobar que esos proveedores están al día con sus obligaciones fiscales y laborales (SAT, IMSS, INFONAVIT). Hoy ese control se hace con carpetas de archivos, correos y hojas de cálculo, lo que genera riesgo de multas, responsabilidad solidaria y horas perdidas.

La plataforma convierte ese desorden documental en **una bóveda organizada y un tablero de gestión de riesgo**: en una sola pantalla se sabe qué proveedor está al corriente, cuál está por vencer y cuál ya incumple, sin abrir un solo archivo.

---

## Capacidades principales (mensajes de venta)

- **Bóveda documental centralizada** de todos los proveedores y sus documentos de cumplimiento.
- **Semáforo de cumplimiento en tiempo real**: vigente, por vencer, vencido o faltante, por proveedor y por documento.
- **Alertas proactivas** por correo e in-app antes y después de cada vencimiento.
- **Catálogo inteligente por industria**: cada tipo de proveedor exige solo los documentos que le corresponden.
- **Portal de autoservicio para el proveedor**: el propio proveedor sube y da seguimiento a su documentación.
- **Lectura automática de documentos (OCR)** para prellenar fechas y RFC al cargar.
- **Reportes y evidencia exportable** para auditorías e inspecciones.
- **Tablero analítico** con gráficos y KPIs de cumplimiento.
- **Multi-tenant con aislamiento total**: los datos de cada cliente están completamente separados.

---

## Módulos y funcionalidad por área

### 1. Bóveda de cumplimiento (núcleo)

- Registro de proveedores con razón social, RFC, contacto, estado y tipo de proveedor (industria).
- Carga de documentos de cumplimiento (PDF, imágenes y formatos ofimáticos) clasificados por tipo y periodo.
- Catálogo precargado de documentos obligatorios REPSE: Opinión de cumplimiento SAT, IMSS, INFONAVIT, ICSOE, SISUB, contrato de servicios, comprobantes de cuotas obrero-patronales, CFDI de nómina, entre otros.
- Periodicidades soportadas: mensual, bimestral, anual y sin vigencia, con cálculo automático de fecha de vencimiento según el calendario fiscal SAT/IMSS (con override manual cuando aplique).
- **OCR best-effort**: al subir un PDF, el sistema lee y prellena fecha de emisión, vigencia y RFC; el usuario puede corregir antes de guardar.
- Histórico de versiones: una nueva carga archiva la anterior, nunca la borra.
- **Trazabilidad visible por documento**: quién lo agregó, quién lo actualizó por última vez y quién lo validó, con fecha y hora; más un historial cronológico completo.
- Verificación manual estructurada: cualquier usuario con permiso marca un documento como "verificado" dejando registro de usuario, fecha y nota.
- Roles internos: administrador, gestor y consulta (solo lectura).

### 2. Estado de cumplimiento por proveedor

- Indicador de cumplimiento agregado por proveedor (porcentaje y conteo por estado).
- Cálculo de "Faltante" únicamente contra los documentos que exige el tipo de proveedor, no contra todo el catálogo.
- Manejo inteligente del calendario: solo se exigen periodos ya iniciados y posteriores al alta del proveedor; los periodos del año anterior sin documento se archivan como "Faltante histórico" sin penalizar el indicador del año en curso.

### 3. Vista de cumplimiento anual (cuadrícula)

- Cuadrícula visual: filas = tipos de documento, columnas = los 12 meses del año.
- **Esferas de color** por celda para identificar de un vistazo el estado: verde (cumplido y validado), amarillo (cumplido sin validar), rojo (incumplido), gris (futuro / no aplica).
- Leyenda de colores siempre visible y tooltips descriptivos en cada celda.
- Mes actual resaltado; encabezado de meses fijo al hacer scroll.
- Sección separada para documentos sin periodicidad mensual (entrega única).
- Refresco automático del grid tras subir un documento, sin recargar la página.
- Click en celda para ver/descargar el documento o subir el faltante.

### 4. Carga múltiple y visualizador de documentos

- Carga de **varios archivos en una sola operación**, con progreso individual y reintento de los que fallen.
- **Visualizador en línea**: ver PDFs, imágenes y otros formatos renderizables directamente en el navegador, sin descarga automática.
- Descarga explícita solo cuando el usuario la solicita; navegación entre archivos sin cerrar el panel.
- Agregar documentos adicionales a un periodo mientras no esté validado.
- **Verificar** archivos individuales y **Validar** el tipo de documento completo (varios comprobantes) directamente desde el visualizador.
- Indicador del número de archivos por celda.

### 5. Alertas y recordatorios

- Proceso diario que evalúa cada documento con vigencia y genera alertas.
- Notificación de **"por vencer"** dentro de la ventana configurable (por defecto 15 días) y recordatorio diario de **"vencido"** hasta su renovación.
- Doble canal: **correo electrónico + notificación in-app**, con enlace directo al documento.
- Configuración por organización: días de antelación, destinatarios y horario; destinatarios específicos por proveedor.
- Agrupación anti-spam (un solo correo por proveedor/día), idempotencia diaria y reintentos ante fallos de envío.
- Silenciamiento de alertas por documento con motivo registrado.

### 6. Administración de catálogos

- **Tipos de documento**: activar/desactivar los canónicos y crear tipos personalizados del cliente.
- **Tipos de proveedor (industrias)**: crear, editar y archivar (Construcción, Servicios profesionales, Transporte, etc.).
- **Requisitos por industria**: definir qué documentos exige cada tipo de proveedor y con qué periodicidad (heredada o sobrescrita).
- Recálculo inmediato del cumplimiento de los proveedores afectados al cambiar requisitos.
- Protecciones: no se elimina lo que tiene dependencias (se archiva); los documentos históricos siempre se conservan.

### 7. Clasificación por sector y giro

- Catálogo de **sectores** económicos y **giros** específicos dependientes del sector (ej. Sector "Construcción" → Giro "Plomería").
- Asignación opcional de sector y giro a cada proveedor, con selector de giro filtrado por sector.
- Filtro de la lista de proveedores por sector y giro combinables.

### 8. Datos de contacto y registro REPSE

- Campo de **nombre de contacto** del proveedor junto a correo y teléfono.
- Campo de **folio REPSE** (registro oficial de la STPS), visible en la ficha y en el portal del proveedor en solo lectura.

### 9. Tablero de control (dashboard analítico)

- Vista de una sola pantalla con el cumplimiento agregado de todos los proveedores.
- **Gráfico de pastel** por estado, **gráfico de barras** por tipo de documento y **KPIs**: cumplimiento global, proveedores activos, proveedores en riesgo, documentos por vencer.
- Filtros por año, tipo de proveedor, tipo de documento, proveedor y estado (codificados en la URL para compartir).
- **Drill-down**: click en una porción del gráfico o un KPI lleva al listado correspondiente con los filtros aplicados.
- Frescura casi-real con invalidación automática al cambiar datos.

### 10. Reportes exportables

- Exportación de cumplimiento en **CSV** (datos) y **PDF** (presentable para auditoría/impresión).
- Alcances: un proveedor, un conjunto filtrado o todos los proveedores del tenant.
- Empaquetado opcional en **ZIP con los archivos originales** organizados por proveedor.
- Modo asíncrono para volúmenes grandes, con notificación cuando el reporte esté listo.
- Cada exportación queda registrada en bitácora; enlaces de descarga protegidos por sesión.

### 11. Portal del proveedor (autoservicio)

- Usuarios con rol "proveedor" vinculados a una empresa específica, con **aislamiento total** entre proveedores.
- **Acceso dedicado**: página de inicio de sesión y menú propios, separados del back-office administrativo.
- **Pantalla de Consulta** (solo lectura): estado de cada tipo de documento (vigente, próximo a vencer, vencido, pendiente de entrega), vencimientos e historial.
- Sección de alertas con documentos próximos a vencer y acceso rápido.
- **Pantalla de Carga**: el proveedor sube sus propios documentos faltantes o vencidos (mes en curso hacia atrás; nunca periodos futuros ni periodos ya cubiertos).
- **Flujo "Enviar a validar"**: el proveedor envía el paquete completo a revisión; el estado pasa a "Pendiente de validación" y queda en cola para contabilidad.
- Ciclo de aprobación: contabilidad aprueba (→ Vigente) o rechaza con motivo obligatorio visible al proveedor (→ se rehabilita la carga).
- Mismo diálogo de carga que el administrativo: multi-archivo, progreso por archivo, validación y reintento.

### 12. Gestión de usuarios

- Asignación de proveedor al crear o editar un usuario con rol "proveedor", con búsqueda por nombre o RFC.
- Listado de usuarios con el proveedor vinculado visible.
- Tabla de usuarios mejorada: nombre clicable que abre un panel de detalle de solo lectura, acciones representadas con íconos + tooltip, diseño responsivo.

---

## Diferenciadores y garantías transversales

- **Aislamiento multi-tenant total**: ningún cliente puede ver datos de otro; validado con pruebas automatizadas.
- **Bitácora de auditoría** completa de todas las acciones relevantes (altas, cargas, eliminaciones, validaciones, exportaciones).
- **Seguridad**: HTTPS, archivos accesibles solo con sesión válida (nunca por URL pública), límite de intentos de autenticación.
- **Retención indefinida** de documentos mientras el cliente esté activo; periodo de gracia de 90 días al darse de baja.
- **Diseño moderno y minimalista** que comunica confianza y robustez; usable en escritorio y con visualización móvil del tablero y detalle.
- **Almacenamiento de archivos con nombres únicos garantizados (UUID)**: dos cargas del mismo archivo nunca colisionan ni se sobrescriben.

---

## Estado de las funcionalidades

| # | Funcionalidad | Estado |
|---|---------------|--------|
| 001 | Bóveda de cumplimiento (núcleo) | Listo |
| 003 | Administración de catálogos | Listo |
| 006 | Vista de cumplimiento anual | Listo |
| 007 | Refresco de grid + leyenda de colores | Listo |
| 008 | Carga múltiple y visualizador | Listo |
| 009 | Portal del proveedor (visor + carga) | Listo |
| 010 | Catálogo de sectores y giros | Listo |
| 011 | Contacto y folio REPSE | Listo |
| 012 | Almacenamiento con UUID | Listo |
| 013 | Separación de pantallas del portal | Listo |
| 014 | Asignar proveedor a usuario | Listo |
| 015 | Mejoras UX a la tabla de usuarios | Listo |
| 002 | Alertas y recordatorios | En diseño |
| 004 | Reportes exportables | En diseño |
| 005 | Tablero de control analítico | En diseño |

---

## Beneficios para el cliente (resumen para cierre de venta)

- **Reduce el riesgo legal** de responsabilidad solidaria y multas por incumplimiento REPSE.
- **Ahorra horas** de revisión manual: el estado de cumplimiento está siempre a la vista.
- **Anticipa vencimientos** con alertas automáticas en lugar de reaccionar tarde.
- **Genera evidencia lista para auditorías** en segundos.
- **Involucra al proveedor** con un portal de autoservicio que descarga trabajo del cliente.
- **Escala** con multi-tenant seguro y catálogos adaptables por industria.
