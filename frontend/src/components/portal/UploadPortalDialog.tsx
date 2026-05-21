import { useState, useRef } from "react";
import { Upload, CheckCircle, XCircle, Loader2, X } from "lucide-react";

import { Button, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { portalApi } from "@/lib/api/portal";
import type { UploadOut } from "@/lib/api/portal";

const ALLOWED_MIME_TYPES = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

const MAX_FILE_BYTES = 20 * 1024 * 1024;

function validateFile(f: File): string | null {
  if (!ALLOWED_MIME_TYPES.has(f.type)) {
    return "Tipo no permitido. Se aceptan PDF, PNG, JPG y DOCX.";
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
    case "upload_not_allowed":
      return "La celda no está en un estado que permita carga. Solo se puede cargar en celdas Faltante, Vencido o Pendiente.";
    case "max_files_reached":
      return "Se alcanzó el límite de archivos para este tipo y período.";
    case "invalid_file_type":
      return "El formato no está permitido para este tipo de documento.";
    case "file_too_large":
      return "El archivo supera el tamaño máximo de este tipo de documento.";
    case "future_period":
      return "No se pueden cargar documentos para períodos futuros.";
    case "supplier_not_linked":
      return "Tu cuenta no está vinculada a ningún proveedor. Contacta al administrador.";
    default:
      return e.message || "Error inesperado al subir el archivo.";
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
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<UploadOut | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileSelect(f: File) {
    const err = validateFile(f);
    setValidationError(err);
    setApiError(null);
    setFile(err ? null : f);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFileSelect(dropped);
  }

  async function handleUpload() {
    if (!file) return;
    setIsUploading(true);
    setApiError(null);
    try {
      const res = await portalApi.upload(file, documentTypeId, coveragePeriodStart ?? undefined);
      setResult(res);
    } catch (e: unknown) {
      setApiError(e instanceof ApiError ? apiErrorMessage(e) : "Error inesperado.");
    } finally {
      setIsUploading(false);
    }
  }

  const periodLabel = coveragePeriodStart
    ? new Date(coveragePeriodStart + "T00:00:00").toLocaleDateString("es-MX", {
        year: "numeric",
        month: "long",
      })
    : null;

  const displayError = validationError ?? apiError;
  const isSuccess = result !== null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Cargar documento</CardTitle>
              <p className="mt-0.5 text-sm text-neutral-600">{documentTypeName}</p>
              {periodLabel && (
                <p className="text-xs text-neutral-500">Período: {periodLabel}</p>
              )}
            </div>
            <button
              type="button"
              className="shrink-0 rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
              onClick={() => onClose(isSuccess)}
              aria-label="Cerrar"
            >
              <X size={18} />
            </button>
          </div>
        </CardHeader>

        <CardBody>
          {isSuccess ? (
            <div className="space-y-4">
              <div className="flex flex-col items-center gap-3 py-4 text-center">
                <CheckCircle size={40} className="text-green-500" />
                <div>
                  <p className="font-semibold text-neutral-800">Documento cargado con éxito</p>
                  <p className="mt-1 text-sm text-neutral-500">{result.file_name_original}</p>
                </div>
              </div>
              <div className="flex justify-end">
                <Button onClick={() => onClose(true)}>Cerrar</Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Zona de arrastre / clic */}
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => !isUploading && inputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
                  isUploading
                    ? "cursor-not-allowed opacity-60"
                    : isDragOver
                    ? "border-brand-400 bg-brand-50"
                    : file
                    ? "border-green-300 bg-green-50"
                    : "border-neutral-300 bg-neutral-50 hover:border-brand-300 hover:bg-brand-50/50"
                }`}
              >
                <Upload size={24} className={file ? "text-green-500" : "text-neutral-400"} />
                {file ? (
                  <div>
                    <p className="text-sm font-medium text-neutral-800">{file.name}</p>
                    <p className="text-xs text-neutral-500">{formatBytes(file.size)}</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-neutral-600">
                      Arrastra un archivo aquí o{" "}
                      <span className="font-medium text-brand-600">selecciona</span>
                    </p>
                    <p className="mt-1 text-xs text-neutral-400">
                      PDF, PNG, JPG o DOCX · máx. 20 MB
                    </p>
                  </div>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  className="hidden"
                  accept="application/pdf,image/png,image/jpeg,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFileSelect(f);
                  }}
                />
              </div>

              {/* Mensaje de error */}
              {displayError && (
                <div className="flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                  <XCircle size={16} className="mt-0.5 shrink-0" />
                  <span>{displayError}</span>
                </div>
              )}

              {/* Progreso de carga */}
              {isUploading && (
                <div className="flex items-center gap-2 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">
                  <Loader2 size={16} className="animate-spin shrink-0" />
                  Subiendo archivo…
                </div>
              )}

              {/* Acciones */}
              <div className="flex justify-end gap-3">
                <Button variant="ghost" onClick={() => onClose(false)} disabled={isUploading}>
                  Cancelar
                </Button>
                <Button
                  onClick={handleUpload}
                  disabled={!file || !!validationError || isUploading}
                >
                  {isUploading ? (
                    <span className="flex items-center gap-1.5">
                      <Loader2 size={14} className="animate-spin" />
                      Subiendo…
                    </span>
                  ) : (
                    "Subir"
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
