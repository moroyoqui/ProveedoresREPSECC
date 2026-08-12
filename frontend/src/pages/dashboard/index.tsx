import { useNavigate, useSearchParams } from "react-router-dom";

import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { ComplianceSummaryTable } from "@/components/dashboard/ComplianceSummaryTable";
import { DashboardFilters as DashboardFilterBar } from "@/components/dashboard/DashboardFilters";
import { DocTypeBarChart } from "@/components/dashboard/DocTypeBarChart";
import { KpiStrip } from "@/components/dashboard/KpiStrip";
import { StatusPieChart } from "@/components/dashboard/StatusPieChart";
import { YearSelect } from "@/components/dashboard/YearSelect";
import {
  useDashboard,
  type DashboardFilters,
  type DashboardStatus,
} from "@/lib/api/dashboard";

function filtersFromParams(sp: URLSearchParams): DashboardFilters {
  const filters: DashboardFilters = {};
  const year = sp.get("year");
  if (year) filters.year = Number(year);
  const stype = sp.getAll("supplier_type").map(Number);
  if (stype.length) filters.supplier_type = stype;
  const dtype = sp.getAll("document_type").map(Number);
  if (dtype.length) filters.document_type = dtype;
  const supplier = sp.getAll("supplier").map(Number);
  if (supplier.length) filters.supplier = supplier;
  const status = sp.getAll("status") as DashboardStatus[];
  if (status.length) filters.status = status;
  if (sp.get("include_inactive") === "true") filters.include_inactive = true;
  return filters;
}

function paramsFromFilters(f: DashboardFilters): URLSearchParams {
  const sp = new URLSearchParams();
  if (f.year) sp.set("year", String(f.year));
  f.supplier_type?.forEach((v) => sp.append("supplier_type", String(v)));
  f.document_type?.forEach((v) => sp.append("document_type", String(v)));
  f.supplier?.forEach((v) => sp.append("supplier", String(v)));
  f.status?.forEach((v) => sp.append("status", v));
  if (f.include_inactive) sp.set("include_inactive", "true");
  return sp;
}

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const filters = filtersFromParams(searchParams);
  const { data, isLoading, isError } = useDashboard(filters);

  function applyFilters(next: DashboardFilters) {
    setSearchParams(paramsFromFilters(next));
  }

  function handleYearChange(year: number) {
    applyFilters({ ...filters, year });
  }

  // Drill-down al listado de documentos (FR-015/016/017). Propaga los filtros
  // de un solo valor compatibles con el listado; la dimensión seleccionada
  // (estado/tipo) llega en `extra`. El listado no filtra por año ni multi-valor.
  function goToDocuments(extra: Record<string, string>) {
    const sp = new URLSearchParams();
    if (filters.document_type?.length === 1)
      sp.set("document_type_id", String(filters.document_type[0]));
    if (filters.supplier?.length === 1)
      sp.set("supplier_id", String(filters.supplier[0]));
    Object.entries(extra).forEach(([k, v]) => sp.set(k, v));
    navigate(`/documents?${sp.toString()}`);
  }

  if (isLoading) {
    return <p className="p-8 text-sm text-neutral-500">Cargando tablero…</p>;
  }
  if (isError || !data) {
    return <p className="p-8 text-sm text-status-expired">No se pudo cargar el tablero.</p>;
  }

  if (data.empty_reason === "no_suppliers") {
    return (
      <div className="mx-auto max-w-3xl p-8 text-center">
        <h1 className="mb-2 text-2xl font-semibold text-brand-700">Tablero de cumplimiento</h1>
        <p className="text-neutral-600">
          Aún no tienes proveedores registrados. Registra tu primer proveedor para ver aquí el
          estado de cumplimiento agregado.
        </p>
      </div>
    );
  }

  const calculatedAt = new Date(data.calculated_at).toLocaleString("es-MX");

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-brand-700">Tablero de cumplimiento</h1>
        <div className="flex items-center gap-4">
          <YearSelect
            value={data.filters.year}
            years={data.available_years}
            onChange={handleYearChange}
          />
          <p className="text-xs text-neutral-400">
            Última actualización: {calculatedAt} (zona del tenant)
          </p>
        </div>
      </header>

      <DashboardFilterBar filters={filters} onChange={applyFilters} />

      <KpiStrip
        kpis={data.kpis}
        onAtRiskClick={() => navigate("/suppliers")}
        onExpiringClick={() => goToDocuments({ status: "expiring_soon" })}
      />

      {data.empty_reason === "no_data_for_filters" ? (
        <Card>
          <CardBody>
            <p className="text-sm text-neutral-500">
              No hay datos para los filtros seleccionados. Ajusta o limpia los filtros.
            </p>
          </CardBody>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Desglose por estado</CardTitle>
            </CardHeader>
            <CardBody>
              <StatusPieChart
                data={data.pie}
                onSliceClick={(status) =>
                  goToDocuments(status === "missing" ? {} : { status })
                }
              />
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cumplimiento por tipo de documento</CardTitle>
            </CardHeader>
            <CardBody>
              <DocTypeBarChart
                data={data.by_document_type}
                onBarClick={(id) => goToDocuments({ document_type_id: String(id) })}
              />
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Resumen por proveedor</CardTitle>
            </CardHeader>
            <CardBody>
              <ComplianceSummaryTable rows={data.suppliers} />
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}
