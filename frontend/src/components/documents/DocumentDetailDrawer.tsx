import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/Button";
import { ComplianceBadge } from "@/components/documents/ComplianceBadge";
import { VerifiedBadge } from "@/components/documents/VerifiedBadge";
import { HistoryTab } from "@/components/documents/HistoryTab";
import { documentsApi } from "@/lib/api/index";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { DocumentListItem } from "@/lib/api/documents";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso + (iso.includes("T") ? "" : "T12:00:00"));
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

type Tab = "info" | "history";

type Props = {
  document: DocumentListItem;
  onClose: () => void;
  onVerify: () => void;
  onUnverifySuccess: () => void;
};

export function DocumentDetailDrawer({ document: doc, onClose, onVerify, onUnverifySuccess }: Props) {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("info");
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [unverifyError, setUnverifyError] = useState<string | null>(null);

  const canVerify = !doc.verified && (user?.role === "admin" || user?.role === "manager");
  const canUnverify = doc.verified && user?.role === "admin";

  const unverify = useMutation({
    mutationFn: () => documentsApi.unverify(doc.id),
    onSuccess: onUnverifySuccess,
    onError: (e: unknown) => {
      setUnverifyError(e instanceof ApiError ? e.message : "Error al quitar verificación.");
    },
  });

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const { token } = await documentsApi.downloadToken(doc.id);
      window.open(`/api/v1/files/${token}`, "_blank");
    } catch (e) {
      setDownloadError(e instanceof ApiError ? e.message : "No se pudo generar el enlace de descarga.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Detalle: ${doc.document_type?.name ?? `Tipo #${doc.document_type_id}`}`}
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[560px] flex-col bg-white shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-neutral-200 px-6 py-4">
          <div className="min-w-0">
            <p className="truncate text-xs font-medium uppercase tracking-wide text-neutral-400">
              {doc.supplier?.legal_name ?? "Proveedor"}
            </p>
            <h2 className="mt-0.5 text-lg font-semibold leading-snug text-brand-800">
              {doc.document_type?.name ?? `Tipo #${doc.document_type_id}`}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="ml-4 shrink-0 rounded-md p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
            aria-label="Cerrar panel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Status bar */}
        <div className="flex items-center gap-3 border-b border-neutral-100 bg-neutral-50 px-6 py-2.5">
          <ComplianceBadge status={doc.status} />
          <VerifiedBadge document={doc} />
          <span className="ml-auto text-xs text-neutral-400">
            v{doc.version}{doc.document_type?.periodicity ? ` · ${doc.document_type.periodicity}` : ""}
          </span>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-neutral-200 px-6">
          {(["info", "history"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`mr-1 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                tab === t
                  ? "border-brand-600 text-brand-700"
                  : "border-transparent text-neutral-500 hover:text-neutral-700"
              }`}
            >
              {t === "info" ? "Información" : "Historial"}
            </button>
          ))}
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {tab === "info" ? (
            <div className="space-y-6">
              {/* Archivo */}
              <section>
                <SectionTitle>Archivo</SectionTitle>
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-all text-sm font-medium text-neutral-800">
                        {doc.file.name}
                      </p>
                      <p className="mt-1 text-xs text-neutral-500">
                        {formatBytes(doc.file.size_bytes)} · {doc.file.mime_type}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={handleDownload}
                      disabled={downloading}
                      className="shrink-0"
                    >
                      {downloading ? "Generando…" : "Descargar"}
                    </Button>
                  </div>
                  {downloadError && (
                    <p className="mt-2 text-xs text-red-600">{downloadError}</p>
                  )}
                </div>
              </section>

              {/* Periodo y vencimiento */}
              <section>
                <SectionTitle>Periodo y vencimiento</SectionTitle>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <InfoItem label="Periodo cubierto">
                    {doc.coverage_period_start
                      ? `${fmtDate(doc.coverage_period_start)}${doc.coverage_period_end ? ` – ${fmtDate(doc.coverage_period_end)}` : ""}`
                      : "—"}
                  </InfoItem>
                  <InfoItem label="Fecha de vencimiento">
                    {fmtDate(doc.due_date_effective)}
                  </InfoItem>
                  {doc.due_date_override_reason && (
                    <InfoItem label="Motivo del ajuste" className="col-span-2">
                      {doc.due_date_override_reason}
                    </InfoItem>
                  )}
                </dl>
              </section>

              {/* OCR */}
              {(doc.ocr.extracted_rfc || doc.ocr.extracted_issued_at || doc.ocr.extracted_valid_until) && (
                <section>
                  <SectionTitle>Datos extraídos por OCR</SectionTitle>
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    {doc.ocr.extracted_rfc && (
                      <InfoItem label="RFC extraído">
                        <span className="font-mono">{doc.ocr.extracted_rfc}</span>
                      </InfoItem>
                    )}
                    {doc.ocr.extracted_issued_at && (
                      <InfoItem label="Fecha de emisión">
                        {fmtDate(doc.ocr.extracted_issued_at)}
                      </InfoItem>
                    )}
                    {doc.ocr.extracted_valid_until && (
                      <InfoItem label="Vigencia OCR">
                        {fmtDate(doc.ocr.extracted_valid_until)}
                      </InfoItem>
                    )}
                  </dl>
                </section>
              )}

              {/* Trazabilidad */}
              <section>
                <SectionTitle>Trazabilidad</SectionTitle>
                <div className="space-y-2">
                  <AuditRow
                    label="Agregado por"
                    user={doc.audit.added.user}
                    at={doc.audit.added.at}
                  />
                  <AuditRow
                    label="Última actualización"
                    user={doc.audit.last_updated?.user}
                    at={doc.audit.last_updated?.at}
                  />
                  <AuditRow
                    label="Validado por"
                    user={doc.audit.validated?.user}
                    at={doc.audit.validated?.at}
                    note={doc.audit.validated?.note ?? undefined}
                  />
                </div>
              </section>
            </div>
          ) : (
            <HistoryTab documentId={doc.id} />
          )}
        </div>

        {/* Footer actions */}
        {(canVerify || canUnverify) && (
          <div className="border-t border-neutral-200 px-6 py-4">
            {unverifyError && (
              <p className="mb-3 text-xs text-red-600">{unverifyError}</p>
            )}
            <div className="flex justify-end gap-2">
              {canVerify && (
                <Button variant="primary" size="sm" onClick={onVerify}>
                  Verificar documento
                </Button>
              )}
              {canUnverify && (
                <Button
                  variant="danger"
                  size="sm"
                  disabled={unverify.isPending}
                  onClick={() => unverify.mutate()}
                >
                  {unverify.isPending ? "Quitando…" : "Quitar verificación"}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">
      {children}
    </h3>
  );
}

function InfoItem({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="text-neutral-500">{label}</dt>
      <dd className="mt-0.5 font-medium text-neutral-800">{children}</dd>
    </div>
  );
}

function AuditRow({
  label,
  user,
  at,
  note,
}: {
  label: string;
  user?: { id: number; display_name: string } | null;
  at?: string | null;
  note?: string;
}) {
  return (
    <div className="flex items-start justify-between rounded-md bg-neutral-50 px-3 py-2 text-sm">
      <span className="mr-3 shrink-0 text-neutral-500">{label}</span>
      {user ? (
        <div className="text-right">
          <span className="font-medium text-neutral-800">{user.display_name}</span>
          {at && (
            <span className="ml-2 text-xs text-neutral-400">{fmtDateTime(at)}</span>
          )}
          {note && (
            <p className="mt-0.5 text-xs italic text-neutral-500">{note}</p>
          )}
        </div>
      ) : (
        <span className="text-neutral-400">—</span>
      )}
    </div>
  );
}
