# Data Model: Catálogo de Sectores y Giros

**Feature**: 010-sector-giro-catalog
**Date**: 2026-06-08

---

## Nuevas tablas

### `sectors`

Catálogo global de sectores económicos. No tiene `organization_id` porque es datos de referencia del sistema (ver research.md, Decisión 1).

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `id` | `BIGINT` | NO (PK, autoincrement) | |
| `name` | `VARCHAR(120)` | NO | Nombre del sector. UNIQUE globalmente. |

**Índices**:
- `uq_sectors_name` — `UNIQUE (name)` — garantiza unicidad global de nombres.

**Reglas de negocio**:
- El nombre es único en toda la tabla (case-insensitive a nivel de aplicación, UNIQUE a nivel de DB).
- No se puede eliminar un sector si tiene giros asociados (FK RESTRICT en `giros.sector_id`).
- No se puede eliminar un sector si está asignado a algún proveedor (FK RESTRICT en `suppliers.sector_id`).

---

### `giros`

Catálogo global de giros empresariales. Cada giro pertenece a exactamente un sector.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `id` | `BIGINT` | NO (PK, autoincrement) | |
| `sector_id` | `BIGINT` | NO | FK → `sectors.id` ON DELETE RESTRICT |
| `name` | `VARCHAR(120)` | NO | Nombre del giro. UNIQUE dentro del mismo sector. |

**Índices**:
- `uq_giros_sector_name` — `UNIQUE (sector_id, name)` — garantiza unicidad de nombre dentro del sector.
- `ix_giros_sector_id` — índice simple en `sector_id` para el filtro por sector.

**Reglas de negocio**:
- El nombre es único dentro del mismo `sector_id` (case-insensitive a nivel de aplicación).
- Giros con el mismo nombre en distintos sectores están permitidos.
- No se puede eliminar un giro si está asignado a algún proveedor (FK RESTRICT en `suppliers.giro_id`).
- El `sector_id` de un giro puede editarse (mover el giro a otro sector). Los proveedores que tenían ese giro asignado no se modifican automáticamente (ver edge case en spec.md).

---

## Tabla modificada: `suppliers`

Se agregan dos columnas opcionales de clasificación. Ambas son nullable para preservar compatibilidad con registros existentes.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `sector_id` | `BIGINT` | YES | FK → `sectors.id` ON DELETE RESTRICT. NULL = "sin clasificar". |
| `giro_id` | `BIGINT` | YES | FK → `giros.id` ON DELETE RESTRICT. NULL = "sin clasificar". |

**Índices**:
- `ix_suppliers_sector_id` — simple, para queries de filtrado por sector.
- `ix_suppliers_giro_id` — simple, para queries de filtrado por giro.

**Reglas de negocio**:
- Si `giro_id` está definido, el giro asignado DEBE pertenecer al mismo `sector_id` que tiene el proveedor. Validado en la capa de aplicación.
- Si se cambia `sector_id`, se debe limpiar `giro_id` (o proveer uno nuevo coherente). Validado en la capa de aplicación.
- Un proveedor puede tener `sector_id` sin `giro_id` (clasificación parcial permitida).
- Si `sector_id IS NULL`, entonces `giro_id` DEBE ser NULL. Validado en la capa de aplicación.

---

## Migración Alembic

### `0007_add_sectors_giros`

```sql
-- 1. Nueva tabla sectors
CREATE TABLE sectors (
  id    BIGINT NOT NULL AUTO_INCREMENT,
  name  VARCHAR(120) NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_sectors_name UNIQUE (name)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- 2. Nueva tabla giros
CREATE TABLE giros (
  id        BIGINT NOT NULL AUTO_INCREMENT,
  sector_id BIGINT NOT NULL,
  name      VARCHAR(120) NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_giros_sector_name UNIQUE (sector_id, name),
  INDEX ix_giros_sector_id (sector_id),
  CONSTRAINT fk_giros_sector FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE RESTRICT
) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- 3. Extensión de suppliers
ALTER TABLE suppliers
  ADD COLUMN sector_id BIGINT NULL DEFAULT NULL AFTER supplier_type_id,
  ADD COLUMN giro_id   BIGINT NULL DEFAULT NULL AFTER sector_id,
  ADD INDEX  ix_suppliers_sector_id (sector_id),
  ADD INDEX  ix_suppliers_giro_id   (giro_id),
  ADD CONSTRAINT fk_suppliers_sector FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_suppliers_giro   FOREIGN KEY (giro_id)   REFERENCES giros(id)   ON DELETE RESTRICT;
```

---

## Modelos SQLAlchemy (nuevo)

### `Sector` (repse/sectors/models.py)

```python
class Sector(Base, TimestampMixin):
    __tablename__ = "sectors"
    __table_args__ = (UniqueConstraint("name", name="uq_sectors_name"),)

    id:   Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
```

**Nota**: No hereda `TenantOwned` (catálogo global).

### `Giro` (repse/giros/models.py)

```python
class Giro(Base, TimestampMixin):
    __tablename__ = "giros"
    __table_args__ = (UniqueConstraint("sector_id", "name", name="uq_giros_sector_name"),)

    id:        Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sector_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False, index=True)
    name:      Mapped[str] = mapped_column(String(120), nullable=False)
```

---

## Schemas de API (resumen de cambios)

### Nuevos schemas

**`SectorIn`**: `name: str` (min 2, max 120)
**`SectorOut`**: `id: int`, `name: str`

**`GiroIn`**: `sector_id: int`, `name: str` (min 2, max 120)
**`GiroOut`**: `id: int`, `sector_id: int`, `sector_name: str`, `name: str`
**`GiroBrief`**: `id: int`, `name: str` (para el selector en cascada)

### Extensión de schemas existentes

**`SupplierIn` / `SupplierPatch`** (repse/suppliers/schemas.py):
```
sector_id: int | None = None
giro_id:   int | None = None
```

**`SupplierListItem`** (repse/suppliers/schemas.py):
```
sector: SectorOut | None = None
giro:   GiroBrief | None = None
```

**`SupplierDetailOut`** (repse/suppliers/schemas.py):
```
sector: SectorOut | None = None
giro:   GiroBrief | None = None
```

**Portal compliance response** (repse/portal/schemas.py — nueva key en raíz):
```
sector: SectorOut | None = None
giro:   GiroBrief | None = None
```

---

## Relaciones entre entidades

```
sectors (global)
  │
  ├── giros (global, N:1 → sector)
  │
suppliers (tenant-scoped por organization_id)
  ├── sector_id → sectors.id  (nullable)
  └── giro_id   → giros.id    (nullable; giro.sector_id DEBE == supplier.sector_id)
```

El aislamiento de tenant se mantiene en `suppliers`. Los catálogos `sectors` y `giros` son referencias de solo lectura desde la perspectiva de los datos de negocio del tenant.
