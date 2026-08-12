/** Metadatos compartidos de los 4 estados del tablero (spec 005). */
import type { DashboardStatus } from "@/lib/api/dashboard";

export const STATUS_META: Record<
  DashboardStatus,
  { label: string; color: string }
> = {
  valid: { label: "Vigente", color: "#15803D" },
  expiring_soon: { label: "Por vencer", color: "#B45309" },
  expired: { label: "Vencido", color: "#B91C1C" },
  missing: { label: "Faltante", color: "#525252" },
};

export const STATUS_ORDER: DashboardStatus[] = [
  "valid",
  "expiring_soon",
  "expired",
  "missing",
];
