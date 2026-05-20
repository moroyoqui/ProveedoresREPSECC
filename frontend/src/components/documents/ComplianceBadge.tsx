import { Badge } from "@/components/ui";

type ComplianceStatus = "valid" | "expiring_soon" | "expired" | "missing";

const LABEL: Record<ComplianceStatus, string> = {
  valid: "Vigente",
  expiring_soon: "Por vencer",
  expired: "Vencido",
  missing: "Faltante",
};

const TONE: Record<ComplianceStatus, "valid" | "expiring" | "expired" | "missing"> = {
  valid: "valid",
  expiring_soon: "expiring",
  expired: "expired",
  missing: "missing",
};

export function ComplianceBadge({ status }: { status: ComplianceStatus | string }) {
  const tone = TONE[status as ComplianceStatus] ?? "neutral";
  const label = LABEL[status as ComplianceStatus] ?? status;
  return <Badge tone={tone}>{label}</Badge>;
}
