import type { CellStatus } from "@/lib/api/index";

const COLOR: Record<CellStatus, string> = {
  validated: "bg-green-500",
  submitted: "bg-yellow-400",
  expired: "bg-red-700",
  missing: "bg-red-500",
  pending: "bg-gray-300",
  future: "bg-gray-200",
  not_required: "",
};

const LABEL: Record<CellStatus, string> = {
  validated: "Validado",
  submitted: "Pendiente de validación",
  expired: "Vencido",
  missing: "Faltante",
  pending: "En plazo",
  future: "Mes futuro",
  not_required: "No aplica",
};

const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

export type ComplianceCellProps = {
  status: CellStatus;
  month?: number;
  size?: "sm" | "md";
};

export function ComplianceCell({ status, month, size = "md" }: ComplianceCellProps) {
  if (status === "not_required") {
    return (
      <span
        className="block h-full w-full"
        aria-label={month ? `${MONTH_NAMES[month - 1]}: no aplica` : "No aplica"}
      />
    );
  }

  const tooltip = month ? `${MONTH_NAMES[month - 1]}: ${LABEL[status]}` : LABEL[status];
  const dotSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";

  return (
    <span
      role="img"
      aria-label={tooltip}
      title={tooltip}
      className={`inline-block ${dotSize} rounded-full ${COLOR[status]} ring-1 ring-inset ring-black/5`}
    />
  );
}

export const COMPLIANCE_LEGEND: Array<{ status: CellStatus; label: string }> = [
  { status: "validated", label: "Validado" },
  { status: "submitted", label: "Pendiente de validación" },
  { status: "expired", label: "Vencido" },
  { status: "missing", label: "Faltante" },
  { status: "pending", label: "En plazo" },
  { status: "future", label: "Mes futuro" },
];
