import { Badge } from "@/components/ui";

const LABEL: Record<string, string> = {
  valid: "Vigente",
  expiring_soon: "Por vencer",
  expired: "Vencido",
  missing: "Faltante",
};

const TONE: Record<string, "valid" | "expiring" | "expired" | "missing"> = {
  valid: "valid",
  expiring_soon: "expiring",
  expired: "expired",
  missing: "missing",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={TONE[status] || "neutral"}>{LABEL[status] || status}</Badge>;
}
