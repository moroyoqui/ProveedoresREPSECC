# Quickstart: Grid Refresh & Color Legend (007)

## Cambios en 3 archivos, 0 cambios de backend

### 1. `UploadDialog.tsx` — Refresco del grid

En `onSuccess` del mutation de carga, agregar una segunda invalidación:

```typescript
onSuccess: () => {
  qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
  // NUEVO: invalida el compliance grid de todos los años del proveedor
  qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] });
  onClose(true);
},
```

**Por qué funciona**: React Query hace matching por prefijo. `["supplier-compliance", supplierId]` invalida cualquier query cuya clave empiece así, incluyendo `["supplier-compliance", supplierId, 2026]`.

---

### 2. `ComplianceCell.tsx` — Agregar `not_required` a la leyenda

Al final del archivo, extender el array `COMPLIANCE_LEGEND`:

```typescript
export const COMPLIANCE_LEGEND: Array<{ status: CellStatus; label: string }> = [
  { status: "validated",    label: "Validado" },
  { status: "submitted",    label: "Pendiente de validación" },
  { status: "expired",      label: "Vencido" },
  { status: "missing",      label: "Faltante" },
  { status: "pending",      label: "En plazo" },
  { status: "future",       label: "Mes futuro" },
  { status: "not_required", label: "No aplica" },   // NUEVO
];
```

El componente `ComplianceCell` renderiza `not_required` como un `<span>` vacío. En la leyenda, `ComplianceLegend` usará un estilo especial para este estado (ver punto 3).

---

### 3. `ComplianceGrid.tsx` — Rediseñar la leyenda visual

Reemplazar el componente `ComplianceLegend` local por un recuadro con borde y título:

```typescript
function ComplianceLegend() {
  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">
        Leyenda
      </p>
      <ul className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3 lg:grid-cols-4 text-xs text-neutral-600">
        {COMPLIANCE_LEGEND.map((item) => (
          <li key={item.status} className="flex items-center gap-2">
            <LegendSwatch status={item.status} />
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function LegendSwatch({ status }: { status: CellStatus }) {
  if (status === "not_required") {
    return (
      <span className="inline-block h-3 w-3 flex-shrink-0 rounded-full border border-dashed border-neutral-300 bg-neutral-100" />
    );
  }
  return <ComplianceCell status={status} size="sm" />;
}
```

---

## Verificación rápida

1. Sube un documento desde el detalle de un proveedor → la celda del grid debe cambiar de estado sin recargar la página.
2. Verifica que la leyenda muestra 7 ítems (incluyendo "No aplica") dentro de un recuadro con borde y título "Leyenda".
3. Compara los colores de la leyenda con los del grid — deben ser idénticos.
