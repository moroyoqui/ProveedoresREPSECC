type Counts = {
  valid: number;
  expiring_soon: number;
  expired: number;
  missing: number;
};

export function ComplianceSummary({
  percent,
  counts,
}: {
  percent: number;
  counts: Counts;
}) {
  const total = counts.valid + counts.expiring_soon + counts.expired + counts.missing;

  return (
    <div className="flex flex-wrap items-center gap-6">
      <div className="shrink-0 text-center">
        <p className="text-3xl font-semibold text-brand-700">{percent}%</p>
        <p className="text-xs uppercase tracking-wide text-neutral-500">cumplimiento</p>
      </div>

      {total > 0 && (
        <div className="flex-1">
          <div className="mb-1.5 flex h-2 overflow-hidden rounded-full bg-neutral-100">
            <Bar value={counts.valid} total={total} className="bg-status-valid" />
            <Bar value={counts.expiring_soon} total={total} className="bg-status-expiring" />
            <Bar value={counts.expired} total={total} className="bg-status-expired" />
            <Bar value={counts.missing} total={total} className="bg-neutral-300" />
          </div>
          <div className="grid grid-cols-4 gap-3 text-center text-sm">
            <Stat label="Vigentes" value={counts.valid} tone="text-status-valid" />
            <Stat label="Por vencer" value={counts.expiring_soon} tone="text-status-expiring" />
            <Stat label="Vencidos" value={counts.expired} tone="text-status-expired" />
            <Stat label="Faltantes" value={counts.missing} tone="text-status-missing" />
          </div>
        </div>
      )}
    </div>
  );
}

function Bar({
  value,
  total,
  className,
}: {
  value: number;
  total: number;
  className: string;
}) {
  if (value === 0 || total === 0) return null;
  return (
    <div
      className={className}
      style={{ width: `${(value / total) * 100}%` }}
      aria-hidden="true"
    />
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div>
      <p className={`text-lg font-semibold ${tone}`}>{value}</p>
      <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
    </div>
  );
}
