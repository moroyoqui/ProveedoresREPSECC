/**
 * Dashboard de cumplimiento (spec 005).
 *
 * Cliente TanStack Query del endpoint agregado por tenant
 * `GET /api/v1/dashboard/compliance`. Los tipos reflejan
 * `contracts/dashboard-api.md`.
 */

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";

export type DashboardStatus = "valid" | "expiring_soon" | "expired" | "missing";

export type DashboardFilters = {
  year?: number;
  supplier_type?: number[];
  document_type?: number[];
  supplier?: number[];
  status?: DashboardStatus[];
  include_inactive?: boolean;
};

export type PieSlice = {
  status: DashboardStatus;
  count: number;
  percent: number;
};

export type DocTypeBar = {
  document_type_id: number;
  name: string;
  inactive: boolean;
  valid: number;
  expiring_soon: number;
  expired: number;
  missing: number;
  compliance_percent: number;
};

export type Kpis = {
  global_compliance_percent: number;
  active_suppliers: number;
  at_risk_suppliers: number;
  expiring_30d: number;
};

export type SupplierRow = {
  supplier_id: number;
  legal_name: string;
  rfc: string;
  supplier_type: string | null;
  status: string;
  compliance_percent: number;
  expired: number;
  missing: number;
};

export type DashboardOut = {
  filters: Required<Omit<DashboardFilters, "year">> & { year: number };
  pie: PieSlice[];
  by_document_type: DocTypeBar[];
  kpis: Kpis;
  suppliers: SupplierRow[];
  available_years: number[];
  calculated_at: string;
  empty_reason: "no_suppliers" | "no_data_for_filters" | null;
};

function buildQuery(filters: DashboardFilters): string {
  const params = new URLSearchParams();
  if (filters.year != null) params.set("year", String(filters.year));
  filters.supplier_type?.forEach((id) => params.append("supplier_type", String(id)));
  filters.document_type?.forEach((id) => params.append("document_type", String(id)));
  filters.supplier?.forEach((id) => params.append("supplier", String(id)));
  filters.status?.forEach((s) => params.append("status", s));
  if (filters.include_inactive) params.set("include_inactive", "true");
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function fetchDashboard(filters: DashboardFilters): Promise<DashboardOut> {
  return apiFetch<DashboardOut>(`/dashboard/compliance${buildQuery(filters)}`);
}

export function useDashboard(filters: DashboardFilters) {
  return useQuery({
    queryKey: ["dashboard", "compliance", filters],
    queryFn: () => fetchDashboard(filters),
  });
}
