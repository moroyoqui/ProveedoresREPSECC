import { useState } from "react";
import { CheckCircle, XCircle, Loader2, RefreshCcw, X } from "lucide-react";

import { Button, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { portalApi } from "@/lib/api/portal";

const ALLOWED_MIME_TYPES = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

const MAX_FILE_BYTES = 20 * 1024 * 1024;

type FileStatus = "idle" | "uploading" | "success" | "error";

type FileItem = {
  file: File;
  status: FileStatus;
  error?: string;
};

function validateFile(f: File): string | null {
  if (!ALLOWED_MIME_TYPES.has(f.type)) {
    return `Tipo no permitido: ${f.type || "desconocido"}. Se aceptan PDF, PNG, JPG y DOCX.`;
  }
  if (f.size > MAX_FILE_BYTES) {
    return `El archivo supera el tamaño máximo (${Math.round(MAX_FILE_BYTES / (1024 * 1024))} MB).`;
  }
  return null;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function apiErrorMessage(e: ApiError): string {
  switch (e.code) {
    case "duplicate_file":
      return "Archivo duplicado (ya existe).";
    case "upload_not_allowed":
      return "La celda no está en un estado que permita carga.";
    case "max_files_reached":
      return "Se alcanzó el límite de archivos para este tipo y período.";
    case "invalid_file_type":
      return "El formato no está permitido para este tipo de documento.";
    case "file_too_large":
      return "El archivo supera el tamaño máximo permitido.";
    case "future_period":
      return "No se pueden cargar documentos para períodos futuros.";
    case "supplier_not_linked":
      return "Tu cuenta no está vinculada a ningún proveedor. Contacta al administrador.";
    default:
      return e.message || "Error inesperado al subir el archivo.";
  }
}

function FileStatusIcon({ status }: { status: FileStatus }) {
  switch (status) {
    case "uploading":
      return <Loader2 size={16} className="shrink-0 animate-spin text-blue-500" />;
    case "success":
      return <CheckCircle size={16} className="shrink-0 text-green-500" />;
    case "error":
      return <XCircle size={16} className="shrink-0 text-status-expired" />;
    default:
      return <span className="h-4 w-4 shrink-0 rounded-full border border-neutral-300" />;
  }
}

export function UploadPortalDialog({
  documentTypeId,
  documentTypeName,
  coveragePeriodStart,
  onClose,
}: {
  documentTypeId: number;
  documentTypeName: string;
  coveragePeriodStart: string | null;
  onClose: (uploaded?: boolean) => void;
}) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const periodLabel = coveragePeriodStart
    ? new Date(coveragePeriodStart + "T00:00:00").toLocaleDateString("es-MX", {
        year: "numeric",
        month: "long",
      })
    : null;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(e.target.files ?? []);
    if (selected.length === 0) return;
    const items: FileItem[] = selected.map((file) => {
      const err = validateFile(file);
      return { file, status: err ? "error" : "idle", error: err ?? undefined };
    });
    setFiles(items);
    setGlobalError(null);
  }

  function handleRetryFailed() {
    setFiles((prev) =>
      prev.map((item) =>
        item.status === "error" ? { ...item, status: "idle", error: undefined } : item
      )
    );
    setGlobalError(null);
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const uploadable = files.filter((f) => f.status === "idle");
    if (uploadable.length === 0) {
      setGlobalError("Selecciona al menos un archivo válido para subir.");
      return;
    }

    setGlobalError(null);
    setIsUploading(true);
    let anySuccess = false;

    for (const item of uploadable) {
      setFiles((prev) =>
        prev.map((f) => (f.file === item.file ? { ...f, status: "uploading" } : f))
      );

      try {
        await portalApi.upload(
          item.file,
          documentTypeId,
          coveragePeriodStart ?? undefined,
        );
        setFiles((prev) =>
          prev.map((f) => (f.file === item.file ? { ...f, status: "success" } : f))
        );
        anySuccess = true;
      } catch (e: unknown) {
        const msg =
          e instanceof ApiError ? apiErrorMessage(e) : "Error inesperado.";
        setFiles((prev) =>
          prev.map((f) => (f.file === item.file ? { ...f, status: "error", error: msg } : f))
        );
      }
    }

    setIsUploading(false);

    const hasFailed = files.some((f) => f.status === "error");
    if (anySuccess && !hasFailed) {
      onClose(true);
    }
  }

  const successCount = files.filter((f) => f.status === "success").length;
  const hasRetryable = files.some(
    (f) =>
      f.status === "error" &&
      !f.error?.startsWith("Tipo") &&
      !f.error?.startsWith("El archivo")
  );
  const hasAtLeastOneSuccess = successCount > 0;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Subir documento</CardTitle>
              <p className="mt-0.5 text-sm text-neutral-600">{documentTypeName}</p>
              {periodLabel && (
                <p className="text-xs text-neutral-500">Período: {periodLabel}</p>
              )}
            </div>
            <button
              type="button"
              className="shrink-0 rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
              onClick={() => onClose(hasAtLeastOneSuccess)}
              aria-label="Cerrar"
            >
              <X size={18} />
            </button>
          </div>
        </CardHeader>

        <CardBody>
          {globalError && (
            <p className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">
              {globalError}
            </p>
          )}
          {isUploading && (
            <p className="mb-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">
              Subiendo archivos… Por favor espera.
            </p>
          )}
          {!isUploading && successCount > 0 && files.some((f) => f.status === "error") && (
            <p className="mb-3 rounded-md bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
              {successCount} de {files.length} archivos subidos correctamente.
            </p>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-brand-700" htmlFor="portal-upload-file">
                Archivos
              </label>
              <input
                id="portal-upload-file"
                type="file"
                multiple
                accept="application/pdf,image/png,image/jpeg,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="mt-1.5 block w-full text-sm"
                onChange={handleFileChange}
                disabled={isUploading}
              />
              <p className="mt-1 text-xs text-neutral-400">
                PDF, PNG, JPG o DOCX · máx. {Math.round(MAX_FILE_BYTES / (1024 * 1024))} MB por archivo
              </p>
            </div>

            {files.length > 0 && (
              <ul className="divide-y divide-neutral-100 rounded-md border border-neutral-200 text-sm">
                {files.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 px-3 py-2">
                    <FileStatusIcon status={item.status} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-neutral-800">{item.file.name}</p>
                      {item.error ? (
                        <p className="text-xs text-status-expired">{item.error}</p>
                      ) : (
                        <p className="text-xs text-neutral-400">{formatBytes(item.file.size)}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <div className="flex flex-wrap justify-end gap-3 pt-2">
              {hasRetryable && !isUploading && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleRetryFailed}
                  className="gap-1"
                >
                  <RefreshCcw size={14} />
                  Reintentar fallidos
                </Button>
              )}
              <Button
                type="button"
                variant="ghost"
                onClick={() => onClose(hasAtLeastOneSuccess)}
                disabled={isUploading}
              >
                {hasAtLeastOneSuccess ? "Cerrar" : "Cancelar"}
              </Button>
              <Button
                type="submit"
                disabled={isUploading || files.filter((f) => f.status === "idle").length === 0}
              >
                {isUploading ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 size={14} className="animate-spin" />
                    Subiendo…
                  </span>
                ) : (
                  `Subir${files.filter((f) => f.status === "idle").length > 1 ? ` (${files.filter((f) => f.status === "idle").length})` : ""}`
                )}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
