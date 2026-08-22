import { Badge } from "@/components/ui";
import type { DocumentOut } from "@/lib/api/index";

type Props = {
  document: Pick<DocumentOut, "verified" | "audit">;
};

/** Renderiza "Validado" / "Sin validar" con tooltip de usuario y fecha.
 *
 * Spec 017 (FR-011): la interfaz usa una sola palabra, "Validado". El campo
 * interno sigue llamándose `verified` — nadie fuera del código lo ve.
 */
export function VerifiedBadge({ document }: Props) {
  const { verified, audit } = document;

  if (!verified) {
    return <Badge tone="neutral">Sin validar</Badge>;
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
      Validado
    </Badge>
  );
}
