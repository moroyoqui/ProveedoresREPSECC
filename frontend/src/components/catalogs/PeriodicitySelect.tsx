import type { Periodicity } from "@/lib/api/index";

const LABELS: Record<Periodicity, string> = {
  monthly: "Mensual",
  bimonthly: "Bimestral",
  annual: "Anual",
  none: "Sin vigencia",
};

export function periodicityLabel(p: Periodicity): string {
  return LABELS[p] ?? p;
}

export function PeriodicitySelect({
  value,
  onChange,
  includeInherit = false,
  inheritLabel = "Heredar",
  required = false,
  className = "",
  name,
}: {
  value: Periodicity | null;
  onChange: (next: Periodicity | null) => void;
  includeInherit?: boolean;
  inheritLabel?: string;
  required?: boolean;
  className?: string;
  name?: string;
}) {
  return (
    <select
      name={name}
      required={required}
      className={`h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm ${className}`}
      value={value ?? ""}
      onChange={(e) => {
        const v = e.target.value;
        if (v === "") onChange(null);
        else onChange(v as Periodicity);
      }}
    >
      {includeInherit && <option value="">{inheritLabel}</option>}
      <option value="monthly">{LABELS.monthly}</option>
      <option value="bimonthly">{LABELS.bimonthly}</option>
      <option value="annual">{LABELS.annual}</option>
      <option value="none">{LABELS.none}</option>
    </select>
  );
}
