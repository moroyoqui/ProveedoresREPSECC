import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { DocumentListFilters } from "@/lib/api/documents";

type Props = {
  filters: DocumentListFilters;
  onChange: (filters: DocumentListFilters) => void;
};

/**
 * Barra de filtros para la lista global de documentos.
 * Sincroniza el estado con search params de la URL (filtros compartibles vía link).
 * El campo `q` tiene debounce de 300 ms.
 */
export function DocumentFiltersBar({ filters, onChange }: Props) {
  const [, setSearchParams] = useSearchParams();
  const [qDraft, setQDraft] = useState(filters.q ?? "");

  // Debounce para el campo q
  useEffect(() => {
    const t = setTimeout(() => {
      if (qDraft !== (filters.q ?? "")) {
        const next = { ...filters, q: qDraft || undefined };
        onChange(next);
        _syncUrl(next, setSearchParams);
      }
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qDraft]);

  function handleSelect(key: keyof DocumentListFilters, raw: string) {
    const next: DocumentListFilters = { ...filters };
    if (key === "verified") {
      if (raw === "") delete next.verified;
      else next.verified = raw === "true";
    } else if (key === "status") {
      if (raw === "") delete next.status;
      else next.status = raw as DocumentListFilters["status"];
    } else if (key === "supplier_id") {
      if (raw === "") delete next.supplier_id;
      else next.supplier_id = Number(raw);
    } else if (key === "document_type_id") {
      if (raw === "") delete next.document_type_id;
      else next.document_type_id = Number(raw);
    }
    onChange(next);
    _syncUrl(next, setSearchParams);
  }

  return (
    <div className="flex flex-wrap gap-3 pb-4">
      {/* Búsqueda libre */}
      <input
        type="search"
        placeholder="Buscar proveedor…"
        className="h-9 rounded-md border border-neutral-300 px-3 text-sm placeholder:text-neutral-400 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
        value={qDraft}
        onChange={(e) => setQDraft(e.target.value)}
        aria-label="Buscar"
      />

      {/* Validado — spec 017: el parámetro sigue siendo `verified`, el texto no. */}
      <label className="sr-only" htmlFor="filter-verified">
        Validado
      </label>
      <select
        id="filter-verified"
        aria-label="Validado"
        className="h-9 rounded-md border border-neutral-300 px-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
        value={filters.verified == null ? "" : String(filters.verified)}
        onChange={(e) => handleSelect("verified", e.target.value)}
      >
        <option value="">Validado: todos</option>
        <option value="true">Validado</option>
        <option value="false">Sin validar</option>
      </select>

      {/* Estado de vigencia */}
      <label className="sr-only" htmlFor="filter-status">
        Estado
      </label>
      <select
        id="filter-status"
        aria-label="Estado"
        className="h-9 rounded-md border border-neutral-300 px-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
        value={filters.status ?? ""}
        onChange={(e) => handleSelect("status", e.target.value)}
      >
        <option value="">Estado: todos</option>
        <option value="valid">Vigente</option>
        <option value="expiring_soon">Por vencer</option>
        <option value="expired">Vencido</option>
      </select>
    </div>
  );
}

function _syncUrl(
  filters: DocumentListFilters,
  setSearchParams: ReturnType<typeof useSearchParams>[1]
) {
  const sp = new URLSearchParams();
  if (filters.q) sp.set("q", filters.q);
  if (filters.verified != null) sp.set("verified", String(filters.verified));
  if (filters.status) sp.set("status", filters.status);
  if (filters.supplier_id) sp.set("supplier_id", String(filters.supplier_id));
  if (filters.document_type_id) sp.set("document_type_id", String(filters.document_type_id));
  setSearchParams(sp, { replace: true });
}
