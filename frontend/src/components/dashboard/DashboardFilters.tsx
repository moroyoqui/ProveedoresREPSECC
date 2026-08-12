/** Barra de filtros del tablero (spec 005, US3).
 * Filtros multi-selección por tipo de proveedor, tipo de documento, proveedor
 * y estado, más "incluir inactivos" y "Limpiar filtros". El padre persiste los
 * filtros en el URL (FR-008/FR-009). */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui";
import {
  documentTypesApi,
  supplierTypesApi,
  suppliersApi,
} from "@/lib/api/index";
import type { DashboardFilters as Filters, DashboardStatus } from "@/lib/api/dashboard";
import { MultiCheckDropdown, type Option } from "./MultiCheckDropdown";
import { STATUS_META, STATUS_ORDER } from "./statusMeta";

type Props = {
  filters: Filters;
  onChange: (next: Filters) => void;
};

const STATUS_OPTIONS: Option[] = STATUS_ORDER.map((s) => ({
  value: s,
  label: STATUS_META[s].label,
}));

const nums = (xs: number[] | undefined): string[] => (xs ?? []).map(String);

export function DashboardFilters({ filters, onChange }: Props) {
  const [supplierQ, setSupplierQ] = useState("");

  const { data: stypes } = useQuery({
    queryKey: ["supplier-types", "active"],
    queryFn: () => supplierTypesApi.list("active"),
  });
  const { data: dtypes } = useQuery({
    queryKey: ["document-types", "all"],
    queryFn: () => documentTypesApi.list(true),
  });
  const { data: sups } = useQuery({
    queryKey: ["suppliers", "filter", supplierQ],
    queryFn: () => suppliersApi.list(supplierQ ? { q: supplierQ } : {}),
  });

  const supplierTypeOptions: Option[] =
    stypes?.items.map((t) => ({ value: String(t.id), label: t.name })) ?? [];
  const docTypeOptions: Option[] =
    dtypes?.items.map((t) => ({
      value: String(t.id),
      label: t.active ? t.name : `${t.name} (inactivo)`,
    })) ?? [];
  const supplierOptions: Option[] =
    sups?.items.map((s) => ({ value: String(s.id), label: `${s.legal_name} · ${s.rfc}` })) ?? [];

  const hasFilters =
    (filters.supplier_type?.length ?? 0) +
      (filters.document_type?.length ?? 0) +
      (filters.supplier?.length ?? 0) +
      (filters.status?.length ?? 0) >
      0 || filters.include_inactive === true;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <MultiCheckDropdown
        label="Tipo de proveedor"
        options={supplierTypeOptions}
        selected={nums(filters.supplier_type)}
        onChange={(v) => onChange({ ...filters, supplier_type: v.map(Number) })}
      />
      <MultiCheckDropdown
        label="Tipo de documento"
        options={docTypeOptions}
        selected={nums(filters.document_type)}
        onChange={(v) => onChange({ ...filters, document_type: v.map(Number) })}
      />
      <MultiCheckDropdown
        label="Proveedor"
        options={supplierOptions}
        selected={nums(filters.supplier)}
        onChange={(v) => onChange({ ...filters, supplier: v.map(Number) })}
        search={{ value: supplierQ, onChange: setSupplierQ, placeholder: "Nombre o RFC…" }}
        emptyHint="Escribe para buscar"
      />
      <MultiCheckDropdown
        label="Estado"
        options={STATUS_OPTIONS}
        selected={filters.status ?? []}
        onChange={(v) => onChange({ ...filters, status: v as DashboardStatus[] })}
      />
      <label className="flex items-center gap-2 text-sm text-neutral-600">
        <input
          type="checkbox"
          checked={filters.include_inactive ?? false}
          onChange={(e) => onChange({ ...filters, include_inactive: e.target.checked })}
        />
        Incluir inactivos
      </label>
      {hasFilters && (
        <Button variant="ghost" onClick={() => onChange({ year: filters.year })}>
          Limpiar filtros
        </Button>
      )}
    </div>
  );
}
