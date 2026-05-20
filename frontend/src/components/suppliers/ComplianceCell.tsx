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
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

export type UploadClickParams = {
  document_type_id: number;
  coverage_period_start: string | null;
};

export type ViewerClickParams = {
  document_type_id: number;
  coverage_period_start: string | null;
};

export type ComplianceCellProps = {
  status: CellStatus;
  month?: number;
  size?: "sm" | "md";
  document_id?: number | null;
  document_count?: number;
  document_type_id?: number;
  coverage_period_start?: string | null;
  onDocumentClick?: (documentId: number) => void;
  onViewerClick?: (params: ViewerClickParams) => void;
  onUploadClick?: (params: UploadClickParams) => void;
};

export function ComplianceCell({
  status,
  month,
  size = "md",
  document_id,
  document_count,
  document_type_id,
  coverage_period_start,
  onDocumentClick,
  onViewerClick,
  onUploadClick,
}: ComplianceCellProps) {
  const dotSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";

  if (status === "not_required") {
    return (
      <span
        role="img"
        aria-label={month ? `${MONTH_NAMES[month - 1]}: no aplica` : "No aplica"}
        title="No aplica"
        className={`inline-block ${dotSize} shrink-0 rounded-full border border-dashed border-neutral-300 bg-neutral-100`}
      />
    );
  }

  const monthName = month ? MONTH_NAMES[month - 1] : null;
  const label = monthName ? `${monthName}: ${LABEL[status]}` : LABEL[status];
  const sphere = (
    <span
      role="img"
      aria-label={label}
      title={label}
      className={`inline-block ${dotSize} rounded-full ${COLOR[status]} ring-1 ring-inset ring-black/5`}
    />
  );

  const canOpenViewer =
    (status === "validated" || status === "submitted" || status === "expired") &&
    document_type_id != null &&
    onViewerClick != null;

  const canOpenDoc =
    (status === "validated" || status === "submitted" || status === "expired") &&
    document_id != null &&
    onDocumentClick != null &&
    !canOpenViewer;

  const canUpload =
    (status === "missing" || status === "pending") &&
    document_type_id != null &&
    onUploadClick != null;

  const countLabel =
    document_count != null && document_count > 1
      ? ` (${document_count} archivos)`
      : "";
  const countBadge =
    document_count != null && document_count > 1 ? (
      <span
        aria-hidden="true"
        className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-brand-600 text-[9px] font-bold leading-none text-white"
      >
        {document_count > 9 ? "9+" : document_count}
      </span>
    ) : null;

  if (canOpenViewer) {
    return (
      <button
        type="button"
        aria-label={`${label}${countLabel} — ver documentos`}
        title={`${label}${countLabel} — ver documentos`}
        className="relative cursor-pointer rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
        onClick={() =>
          onViewerClick!({ document_type_id: document_type_id!, coverage_period_start: coverage_period_start ?? null })
        }
      >
        {sphere}
        {countBadge}
      </button>
    );
  }

  if (canOpenDoc) {
    return (
      <button
        type="button"
        aria-label={label}
        title={label}
        className="cursor-pointer rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
        onClick={() => onDocumentClick!(document_id!)}
      >
        {sphere}
      </button>
    );
  }

  if (canUpload) {
    return (
      <button
        type="button"
        aria-label={`${label} — haz clic para subir documento`}
        title={`${label} — haz clic para subir`}
        className="cursor-pointer rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
        onClick={() =>
          onUploadClick!({ document_type_id: document_type_id!, coverage_period_start: coverage_period_start ?? null })
        }
      >
        {sphere}
      </button>
    );
  }

  return sphere;
}

export const COMPLIANCE_LEGEND: Array<{ status: CellStatus; label: string }> = [
  { status: "validated", label: "Validado" },
  { status: "submitted", label: "Pendiente de validación" },
  { status: "expired", label: "Vencido" },
  { status: "missing", label: "Faltante" },
  { status: "pending", label: "En plazo" },
  { status: "future", label: "Mes futuro" },
  { status: "not_required", label: "No aplica" },
];
