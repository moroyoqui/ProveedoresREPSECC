import type { BadgeTone } from "@/components/ui";
import type { CellStatus, ComplianceGrid } from "@/lib/api/index";

export const CURRENT_YEAR = new Date().getFullYear();
export const YEAR_OPTIONS = Array.from({ length: CURRENT_YEAR - 2019 }, (_, i) => CURRENT_YEAR - i);

/** Estados que admiten carga desde el portal (regla 009, sin cambios en 013). */
export const PORTAL_UPLOADABLE: ReadonlySet<CellStatus> = new Set(["missing", "pending", "expired"]);

export const MONTH_NAMES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

export function statusTone(status: CellStatus | string | null): BadgeTone {
  switch (status) {
    case "validated":
    case "submitted":     return "valid";
    case "expiring_soon": return "expiring";
    case "expired":
    case "missing":       return "expired";
    case "pending":       return "expiring";
    default:              return "neutral";
  }
}

export function statusLabel(status: CellStatus | string | null): string {
  switch (status) {
    case "validated":     return "Validado";
    case "submitted":     return "En validación";
    case "expiring_soon": return "Por vencer";
    case "expired":       return "Vencido";
    case "missing":       return "Faltante";
    case "pending":       return "Pendiente";
    case "future":        return "Futuro";
    case "not_required":  return "No aplica";
    default:              return status ?? "—";
  }
}

export function computeCounts(data: ComplianceGrid) {
  let valid = 0, expiring_soon = 0, expired = 0, missing = 0;
  for (const req of data.monthly_requirements) {
    for (const cell of req.cells) {
      if (cell.status === "future" || cell.status === "not_required") continue;
      if (cell.status === "validated" || cell.status === "submitted") valid++;
      else if (cell.status === "expired") expired++;
      else if (cell.status === "missing" || cell.status === "pending") missing++;
    }
  }
  for (const req of data.one_time_requirements) {
    if (req.status === "future" || req.status === "not_required") continue;
    if (req.status === "validated" || req.status === "submitted") valid++;
    else if (req.status === "expired") expired++;
    else if (req.status === "missing" || req.status === "pending") missing++;
  }
  return { valid, expiring_soon, expired, missing };
}

/** Celda o requisito único elegible para carga (estados "missing"/"pending"/"expired"). */
export type UploadableItem = {
  document_type_id: number;
  documentTypeName: string;
  coverage_period_start: string | null;
  periodLabel: string;
  status: CellStatus;
};

export function uploadableItems(data: ComplianceGrid): UploadableItem[] {
  const items: UploadableItem[] = [];
  for (const req of data.monthly_requirements) {
    for (const cell of req.cells) {
      if (!PORTAL_UPLOADABLE.has(cell.status)) continue;
      items.push({
        document_type_id: req.document_type.id,
        documentTypeName: req.document_type.name,
        coverage_period_start: cell.coverage_period_start ? String(cell.coverage_period_start) : null,
        periodLabel: `${MONTH_NAMES[cell.month - 1]} ${data.year}`,
        status: cell.status,
      });
    }
  }
  for (const req of data.one_time_requirements) {
    if (!PORTAL_UPLOADABLE.has(req.status)) continue;
    items.push({
      document_type_id: req.document_type.id,
      documentTypeName: req.document_type.name,
      coverage_period_start: null,
      periodLabel: "Documento único",
      status: req.status,
    });
  }
  return items;
}

/** Construye la URL de la pantalla de Carga con el contexto preseleccionado (FR-004). */
export function cargaUrl(item: Pick<UploadableItem, "document_type_id" | "coverage_period_start">): string {
  const params = new URLSearchParams({ type: String(item.document_type_id) });
  if (item.coverage_period_start) params.set("period", item.coverage_period_start);
  return `/portal/carga?${params.toString()}`;
}
