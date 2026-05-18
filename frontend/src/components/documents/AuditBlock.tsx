/**
 * "Agregado / Última actualización / Validado" visible audit trail
 * for a Document (FR-011a + FR-011c spec 001).
 */

import type { DocumentOut } from "@/lib/api/index";

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AuditBlock({ document }: { document: DocumentOut }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Block label="Agregado por">
        <p className="font-medium text-brand-700">{document.audit.added.user.display_name}</p>
        <p className="text-xs text-neutral-500">{fmt(document.audit.added.at)}</p>
      </Block>
      <Block label="Última actualización">
        {document.audit.last_updated ? (
          <>
            <p className="font-medium text-brand-700">
              {document.audit.last_updated.user.display_name}
            </p>
            <p className="text-xs text-neutral-500">{fmt(document.audit.last_updated.at)}</p>
          </>
        ) : (
          <p className="text-sm text-neutral-500">—</p>
        )}
      </Block>
      <Block label="Validado por">
        {document.audit.validated ? (
          <>
            <p className="font-medium text-brand-700">
              {document.audit.validated.user.display_name}
            </p>
            <p className="text-xs text-neutral-500">{fmt(document.audit.validated.at)}</p>
            {document.audit.validated.note && (
              <p className="mt-1 text-xs italic text-neutral-600">
                "{document.audit.validated.note}"
              </p>
            )}
          </>
        ) : (
          <p className="text-sm text-neutral-500">Sin verificar</p>
        )}
      </Block>
    </div>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-3">
      <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
      <div className="mt-1 text-sm">{children}</div>
    </div>
  );
}
