/**
 * Visualizador de documentos para el portal del proveedor.
 * Solo usa portalApi — no importa ningún módulo del back-office.
 */

import { useEffect, useRef, useState } from "react";
import {
  ChevronLeft, ChevronRight, Download, X, RefreshCcw,
  FileText, Plus, Loader2, CheckCircle, XCircle, Upload,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { ApiError } from "@/lib/api";
import { portalApi } from "@/lib/api/portal";
import { Button } from "@/components/ui";
import { SubmitValidationButton } from "@/components/portal/SubmitValidationButton";
import { UPLOAD_ACCEPT, validateUploadFile } from "@/lib/uploadConstraints";

const PREVIEW_MIME_TYPES = new Set([
  "application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp",
]);

type AddFileStatus = "idle" | "uploading" | "success" | "error";
type AddFileItem = { file: File; status: AddFileStatus; error?: string };
type BlobUrlCache = Record<number, string>;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-MX", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export type PortalDocumentViewerParams = {
  supplierId: number;
  documentTypeId: number;
  documentTypeName: string;
  coveragePeriodStart: string | null;
  canAddDocuments?: boolean;
  canSubmit?: boolean;
  onSubmitted?: () => void;
  uploadFn?: (file: File) => Promise<void>;
};

export function PortalDocumentViewerModal({
  documentTypeId,
  documentTypeName,
  coveragePeriodStart,
  canAddDocuments = false,
  canSubmit = false,
  onSubmitted,
  uploadFn,
  onClose,
}: PortalDocumentViewerParams & { onClose: () => void }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [blobUrlCache, setBlobUrlCache] = useState<BlobUrlCache>({});
  const [loadingPreview, setLoadingPreview] = useState(false);
  const blobUrlsRef = useRef<BlobUrlCache>({});
  const [addItems, setAddItems] = useState<AddFileItem[]>([]);
  const addFileRef = useRef<HTMLInputElement>(null);
  const addUploadingRef = useRef(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["documents-list", "portal", documentTypeId, coveragePeriodStart],
    queryFn: () => portalApi.listDocuments(documentTypeId, coveragePeriodStart),
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });

  const docs = data?.items ?? [];
  const selectedDoc = docs[selectedIdx] ?? null;

  useEffect(() => {
    return () => {
      Object.values(blobUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  useEffect(() => {
    if (!selectedDoc) return;
    if (blobUrlCache[selectedDoc.id]) return;
    if (!PREVIEW_MIME_TYPES.has(selectedDoc.file?.mime_type ?? "")) return;

    let cancelled = false;
    setLoadingPreview(true);

    (async () => {
      try {
        const { token } = await portalApi.downloadToken(selectedDoc.id);
        if (cancelled) return;
        const res = await fetch(`/api/v1/files/${token}`, { credentials: "include" });
        if (cancelled || !res.ok) return;
        const blob = await res.blob();
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        blobUrlsRef.current[selectedDoc.id] = url;
        setBlobUrlCache((prev) => ({ ...prev, [selectedDoc.id]: url }));
      } catch {
        // preview unavailable; user can still download
      } finally {
        if (!cancelled) setLoadingPreview(false);
      }
    })();

    return () => { cancelled = true; };
  }, [selectedDoc?.id]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") setSelectedIdx((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setSelectedIdx((i) => Math.min(docs.length - 1, i + 1));
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [docs.length, onClose]);

  useEffect(() => {
    if (docs.length > 0 && selectedIdx >= docs.length) setSelectedIdx(docs.length - 1);
  }, [docs.length]);

  async function handleDownload(docId: number) {
    try {
      const { token } = await portalApi.downloadToken(docId);
      const a = document.createElement("a");
      a.href = `/api/v1/files/${token}`;
      a.rel = "noopener noreferrer";
      a.click();
    } catch {
      // silently fail; user can retry
    }
  }

  async function handleAddFilesSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(e.target.files ?? []);
    if (selected.length === 0) return;
    e.target.value = "";
    if (addUploadingRef.current || !uploadFn) return;

    const initialItems: AddFileItem[] = selected.map((file) => {
      const err = validateUploadFile(file);
      return err ? { file, status: "error", error: err } : { file, status: "idle" as const };
    });
    setAddItems(initialItems);

    const toUpload = initialItems.filter((i) => i.status === "idle");
    if (toUpload.length === 0) return;

    addUploadingRef.current = true;
    let anySuccess = false;

    for (const item of toUpload) {
      setAddItems((prev) => prev.map((i) => (i.file === item.file ? { ...i, status: "uploading" as const } : i)));
      try {
        await uploadFn(item.file);
        setAddItems((prev) => prev.map((i) => (i.file === item.file ? { ...i, status: "success" as const } : i)));
        anySuccess = true;
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : "Error al subir";
        setAddItems((prev) => prev.map((i) => (i.file === item.file ? { ...i, status: "error" as const, error: msg } : i)));
      }
    }

    addUploadingRef.current = false;
    if (anySuccess) {
      refetch();
      setTimeout(() => setAddItems([]), 2000);
    }
  }

  const previewBlobUrl = selectedDoc ? blobUrlCache[selectedDoc.id] : undefined;
  const canPreview = selectedDoc && PREVIEW_MIME_TYPES.has(selectedDoc.file?.mime_type ?? "");
  const isImage = selectedDoc && selectedDoc.file?.mime_type?.startsWith("image/");

  return (
    <>
      <div className="fixed inset-0 z-50 bg-brand-900/50" onClick={onClose} aria-hidden="true" />
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label="Visualizador de documentos"
      >
        <div className="flex h-full max-h-[88vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-2xl">
          {/* Header */}
          <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-5 py-3">
            <div className="flex flex-col gap-1">
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
                          {doc.audit?.added?.at ? ` · ${formatDate(doc.audit.added.at)}` : ""}
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

              {canAddDocuments && uploadFn && (
                <>
                  <hr className="border-neutral-100" />
                  <div className="p-3">
                    <input
                      type="file"
                      multiple
                      accept={UPLOAD_ACCEPT}
                      ref={addFileRef}
                      className="hidden"
                      onChange={handleAddFilesSelected}
                    />
                    <button
                      type="button"
                      onClick={() => addFileRef.current?.click()}
                      disabled={addUploadingRef.current}
                      className="flex w-full items-center justify-center gap-1.5 rounded-md border border-dashed border-brand-300 bg-brand-50 px-3 py-2 text-xs font-medium text-brand-700 hover:bg-brand-100 disabled:opacity-50"
                    >
                      <Plus size={13} />
                      Agregar documento
                    </button>
                    {addItems.length > 0 && (
                      <ul className="mt-2 divide-y divide-neutral-100 rounded-md border border-neutral-200 text-xs">
                        {addItems.map((item, i) => (
                          <li key={i} className="flex items-center gap-2 px-2 py-1.5">
                            <AddItemIcon status={item.status} />
                            <div className="min-w-0 flex-1">
                              <p className="truncate font-medium text-neutral-800">{item.file.name}</p>
                              {item.error ? (
                                <p className="text-status-expired">{item.error}</p>
                              ) : (
                                <p className="text-neutral-400">{formatBytes(item.file.size)}</p>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              )}
            </aside>

            {/* Preview area */}
            <main className="flex min-w-0 flex-1 flex-col bg-neutral-50">
              {selectedDoc ? (
                <>
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
                    <div className="flex items-center gap-2">
                      {canSubmit && onSubmitted && (
                        <SubmitValidationButton
                          documentTypeId={documentTypeId}
                          documentTypeName={documentTypeName}
                          coveragePeriodStart={coveragePeriodStart}
                          onSubmitted={onSubmitted}
                        />
                      )}
                      <Button
                        variant="secondary"
                        className="gap-1 px-3 py-1.5 text-xs"
                        onClick={() => handleDownload(selectedDoc.id)}
                      >
                        <Download size={14} />
                        Descargar
                      </Button>
                    </div>
                  </div>

                  <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto p-4">
                    {loadingPreview && !previewBlobUrl ? (
                      <p className="text-sm text-neutral-400">Cargando vista previa…</p>
                    ) : canPreview && previewBlobUrl ? (
                      isImage ? (
                        <img
                          src={previewBlobUrl}
                          alt={selectedDoc.file?.name ?? "Documento"}
                          className="max-h-full max-w-full rounded object-contain shadow"
                        />
                      ) : (
                        <iframe
                          src={previewBlobUrl}
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
                <div className="flex flex-1 items-center justify-center">
                  {canAddDocuments ? (
                    <div className="flex flex-col items-center gap-3 text-center">
                      <Upload size={40} className="text-neutral-300" />
                      <div>
                        <p className="text-sm font-medium text-neutral-600">No hay documentos todavía</p>
                        <p className="text-xs text-neutral-400">
                          Usa "Agregar documento" en la barra lateral para subir
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-400">Selecciona un archivo de la lista</p>
                  )}
                </div>
              )}
            </main>
          </div>
        </div>
      </div>
    </>
  );
}

function AddItemIcon({ status }: { status: AddFileStatus }) {
  switch (status) {
    case "uploading":
      return <Loader2 size={14} className="shrink-0 animate-spin text-blue-500" />;
    case "success":
      return <CheckCircle size={14} className="shrink-0 text-green-500" />;
    case "error":
      return <XCircle size={14} className="shrink-0 text-status-expired" />;
    default:
      return <span className="h-3.5 w-3.5 shrink-0 rounded-full border border-neutral-300" />;
  }
}
