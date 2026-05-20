import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Download, X, RefreshCcw, FileText } from "lucide-react";

import { documentsApi } from "@/lib/api/index";
import { useDocumentsList } from "@/lib/api/documents";
import { Button } from "@/components/ui";

const PREVIEW_MIME_TYPES = new Set(["application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"]);

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export type DocumentViewerParams = {
  supplierId: number;
  documentTypeId: number;
  documentTypeName: string;
  coveragePeriodStart: string | null;
};

type TokenCache = Record<number, string>;

export function DocumentViewerModal({
  supplierId,
  documentTypeId,
  documentTypeName,
  coveragePeriodStart,
  onClose,
}: DocumentViewerParams & { onClose: () => void }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [tokenCache, setTokenCache] = useState<TokenCache>({});
  const [loadingToken, setLoadingToken] = useState(false);

  const { data, isLoading, isError, refetch } = useDocumentsList({
    supplier_id: supplierId,
    document_type_id: documentTypeId,
    coverage_period_start: coveragePeriodStart ?? undefined,
    is_latest: false,
    limit: 50,
  });

  const docs = data?.items ?? [];
  const selectedDoc = docs[selectedIdx] ?? null;

  // Fetch download token when selected document changes
  useEffect(() => {
    if (!selectedDoc) return;
    if (tokenCache[selectedDoc.id]) return;
    if (!PREVIEW_MIME_TYPES.has(selectedDoc.file?.mime_type ?? "")) return;

    let cancelled = false;
    setLoadingToken(true);
    documentsApi
      .downloadToken(selectedDoc.id)
      .then(({ token }) => {
        if (!cancelled) {
          setTokenCache((prev) => ({ ...prev, [selectedDoc.id]: token }));
        }
      })
      .catch(() => {
        // preview unavailable; user can still download
      })
      .finally(() => {
        if (!cancelled) setLoadingToken(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDoc?.id]);

  // Keyboard: Escape closes, ArrowLeft/Right navigates
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") setSelectedIdx((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setSelectedIdx((i) => Math.min(docs.length - 1, i + 1));
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [docs.length, onClose]);

  // Clamp selectedIdx when docs reload
  useEffect(() => {
    if (docs.length > 0 && selectedIdx >= docs.length) {
      setSelectedIdx(docs.length - 1);
    }
  }, [docs.length]);

  async function handleDownload(docId: number) {
    try {
      const { token } = await documentsApi.downloadToken(docId);
      const a = document.createElement("a");
      a.href = `/api/v1/files/${token}`;
      a.rel = "noopener noreferrer";
      a.click();
    } catch {
      // silently fail; user can retry
    }
  }

  const previewToken = selectedDoc ? tokenCache[selectedDoc.id] : undefined;
  const canPreview = selectedDoc && PREVIEW_MIME_TYPES.has(selectedDoc.file?.mime_type ?? "");
  const isImage = selectedDoc && selectedDoc.file?.mime_type?.startsWith("image/");

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-brand-900/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label="Visualizador de documentos"
      >
        <div className="flex h-full max-h-[88vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-2xl">
          {/* Header */}
          <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-5 py-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-neutral-400">Documentos</p>
              <p className="text-sm font-semibold text-brand-700">{documentTypeName}</p>
              {coveragePeriodStart && (
                <p className="text-xs text-neutral-500">
                  Período:{" "}
                  {new Date(coveragePeriodStart + "T00:00:00").toLocaleDateString("es-MX", {
                    month: "long",
                    year: "numeric",
                  })}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => refetch()}>
                <RefreshCcw size={14} />
                Actualizar
              </Button>
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar visualizador"
                className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="flex min-h-0 flex-1 overflow-hidden">
            {/* File list */}
            <aside className="flex w-64 shrink-0 flex-col border-r border-neutral-200 overflow-y-auto">
              {isLoading && (
                <div className="flex flex-1 items-center justify-center p-6 text-sm text-neutral-400">
                  Cargando…
                </div>
              )}
              {isError && (
                <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-sm text-status-expired">
                  No se pudieron cargar los archivos.
                  <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => refetch()}>
                    Reintentar
                  </Button>
                </div>
              )}
              {!isLoading && !isError && docs.length === 0 && (
                <div className="flex flex-1 items-center justify-center p-6 text-sm text-neutral-400">
                  No hay archivos registrados.
                </div>
              )}
              {!isLoading && docs.length > 0 && (
                <ul className="divide-y divide-neutral-100">
                  {docs.map((doc, idx) => (
                    <li key={doc.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedIdx(idx)}
                        className={`w-full px-4 py-3 text-left text-sm transition-colors hover:bg-neutral-50 ${
                          idx === selectedIdx ? "bg-brand-50 text-brand-700" : "text-neutral-800"
                        }`}
                      >
                        <p className="truncate font-medium">{doc.file?.name ?? `Archivo ${doc.id}`}</p>
                        <p className="text-xs text-neutral-400">
                          {doc.file?.size_bytes != null ? formatBytes(doc.file.size_bytes) : ""}
                          {doc.audit?.added?.at
                            ? ` · ${formatDate(doc.audit.added.at)}`
                            : ""}
                        </p>
                        {doc.verified && (
                          <span className="mt-1 inline-block rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-medium text-green-700">
                            Verificado
                          </span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </aside>

            {/* Preview area */}
            <main className="flex min-w-0 flex-1 flex-col bg-neutral-50">
              {selectedDoc ? (
                <>
                  {/* Preview toolbar */}
                  <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 bg-white px-4 py-2">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedIdx((i) => Math.max(0, i - 1))}
                        disabled={selectedIdx === 0}
                        aria-label="Archivo anterior"
                        className="rounded p-1 text-neutral-500 hover:bg-neutral-100 disabled:opacity-30"
                      >
                        <ChevronLeft size={18} />
                      </button>
                      <span className="text-xs text-neutral-500">
                        {selectedIdx + 1} / {docs.length}
                      </span>
                      <button
                        type="button"
                        onClick={() => setSelectedIdx((i) => Math.min(docs.length - 1, i + 1))}
                        disabled={selectedIdx === docs.length - 1}
                        aria-label="Archivo siguiente"
                        className="rounded p-1 text-neutral-500 hover:bg-neutral-100 disabled:opacity-30"
                      >
                        <ChevronRight size={18} />
                      </button>
                    </div>
                    <Button
                      variant="secondary"
                      className="gap-1 px-3 py-1.5 text-xs"
                      onClick={() => handleDownload(selectedDoc.id)}
                    >
                      <Download size={14} />
                      Descargar
                    </Button>
                  </div>

                  {/* Preview content */}
                  <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto p-4">
                    {loadingToken && !previewToken ? (
                      <p className="text-sm text-neutral-400">Cargando vista previa…</p>
                    ) : canPreview && previewToken ? (
                      isImage ? (
                        <img
                          src={`/api/v1/files/${previewToken}`}
                          alt={selectedDoc.file?.name ?? "Documento"}
                          className="max-h-full max-w-full rounded object-contain shadow"
                        />
                      ) : (
                        <iframe
                          src={`/api/v1/files/${previewToken}`}
                          title={selectedDoc.file?.name ?? "Documento"}
                          className="h-full w-full rounded border border-neutral-200"
                          style={{ minHeight: "500px" }}
                        />
                      )
                    ) : (
                      <div className="flex flex-col items-center gap-4 text-center">
                        <FileText size={48} className="text-neutral-300" />
                        <div>
                          <p className="text-sm font-medium text-neutral-600">
                            {selectedDoc.file?.name ?? "Archivo"}
                          </p>
                          <p className="text-xs text-neutral-400">
                            Vista previa no disponible para este tipo de archivo
                          </p>
                        </div>
                        <Button
                          variant="secondary"
                          className="gap-1"
                          onClick={() => handleDownload(selectedDoc.id)}
                        >
                          <Download size={14} />
                          Descargar archivo
                        </Button>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex flex-1 items-center justify-center text-sm text-neutral-400">
                  Selecciona un archivo de la lista
                </div>
              )}
            </main>
          </div>
        </div>
      </div>
    </>
  );
}
