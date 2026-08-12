/** Tira de KPIs del tablero (spec 005, US1/US4). */
import { Card, CardBody } from "@/components/ui";
import type { Kpis } from "@/lib/api/dashboard";

type Props = {
  kpis: Kpis;
  onAtRiskClick?: () => void;
  onExpiringClick?: () => void;
};

export function KpiStrip({ kpis, onAtRiskClick, onExpiringClick }: Props) {
  const pct = kpis.global_compliance_percent;
  const pctTone =
    pct >= 80 ? "text-status-valid" : pct >= 50 ? "text-status-expiring" : "text-status-expired";

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Kpi label="Cumplimiento global" value={`${pct}%`} tone={pctTone} />
      <Kpi label="Proveedores activos" value={kpis.active_suppliers} tone="text-brand-700" />
      <Kpi
        label="En riesgo"
        value={kpis.at_risk_suppliers}
        tone={kpis.at_risk_suppliers > 0 ? "text-status-expired" : "text-neutral-500"}
        hint="Vencidos o faltantes"
        onClick={onAtRiskClick}
      />
      <Kpi
        label="Por vencer (30 d)"
        value={kpis.expiring_30d}
        tone={kpis.expiring_30d > 0 ? "text-status-expiring" : "text-neutral-500"}
        onClick={onExpiringClick}
      />
    </div>
  );
}

function Kpi({
  label,
  value,
  tone,
  hint,
  onClick,
}: {
  label: string;
  value: number | string;
  tone: string;
  hint?: string;
  onClick?: () => void;
}) {
  return (
    <Card>
      <CardBody>
        <button
          type="button"
          disabled={!onClick}
          onClick={onClick}
          className={`w-full text-left ${onClick ? "cursor-pointer" : "cursor-default"}`}
        >
          <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
          <p className={`mt-1 text-3xl font-semibold ${tone}`}>{value}</p>
          {hint && <p className="mt-1 text-xs text-neutral-400">{hint}</p>}
        </button>
      </CardBody>
    </Card>
  );
}
