import { useQuery } from "@tanstack/react-query";

import { suppliersApi, type SupplierListItem } from "@/lib/api/index";
import { Card, CardBody } from "@/components/ui";

function derive(items: SupplierListItem[]) {
  const active = items.filter((s) => s.status === "active");
  const globalPercent =
    active.length > 0
      ? Math.round(active.reduce((sum, s) => sum + s.compliance_percent, 0) / active.length)
      : 0;
  const atRisk = active.filter((s) => s.counts.expired > 0).length;
  const expiringSoon = active.filter((s) => s.counts.expiring_soon > 0).length;
  return { activeCount: active.length, globalPercent, atRisk, expiringSoon };
}

export function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["suppliers", {}],
    queryFn: () => suppliersApi.list({ status: "active" }),
  });

  const stats = data ? derive(data.items) : null;

  if (isLoading) {
    return <p className="p-8 text-sm text-neutral-500">Cargando tablero…</p>;
  }

  if (isError || !stats) {
    return <p className="p-8 text-sm text-status-expired">No se pudo cargar el tablero.</p>;
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-6 text-2xl font-semibold text-brand-700">Tablero</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Proveedores activos"
          value={stats.activeCount}
          tone="text-brand-700"
        />
        <StatCard
          label="Cumplimiento global"
          value={`${stats.globalPercent}%`}
          tone={
            stats.globalPercent >= 80
              ? "text-status-valid"
              : stats.globalPercent >= 50
              ? "text-status-expiring"
              : "text-status-expired"
          }
        />
        <StatCard
          label="En riesgo"
          value={stats.atRisk}
          tone={stats.atRisk > 0 ? "text-status-expired" : "text-neutral-500"}
          hint="Proveedores con documentos vencidos"
        />
        <StatCard
          label="Por vencer (30 d)"
          value={stats.expiringSoon}
          tone={stats.expiringSoon > 0 ? "text-status-expiring" : "text-neutral-500"}
          hint="Proveedores con documentos próximos a vencer"
        />
      </div>

      {data.has_more && (
        <p className="mt-4 text-xs text-neutral-400">
          Los totales se calculan sobre los primeros resultados cargados. Amplía los filtros para ver
          todos los proveedores.
        </p>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: number | string;
  tone: string;
  hint?: string;
}) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
        <p className={`mt-1 text-3xl font-semibold ${tone}`}>{value}</p>
        {hint && <p className="mt-1 text-xs text-neutral-400">{hint}</p>}
      </CardBody>
    </Card>
  );
}
