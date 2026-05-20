import { Badge } from "@/components/ui";
import type { DocumentOut } from "@/lib/api/index";

type Props = {
  document: Pick<DocumentOut, "verified" | "audit">;
};

/** Renderiza "Verificado" / "Sin verificar" con tooltip de usuario y fecha (FR-011c). */
export function VerifiedBadge({ document }: Props) {
  const { verified, audit } = document;

  if (!verified) {
    return <Badge tone="neutral">Sin verificar</Badge>;
  }

  const validated = audit.validated;
  const tooltip = validated
    ? `${validated.user?.display_name ?? "Sistema"} · ${new Date(validated.at).toLocaleDateString("es-MX")}`
    : undefined;

  return (
    <Badge
      tone="valid"
      title={tooltip}
      className="cursor-default"
    >
      Verificado
    </Badge>
  );
}
