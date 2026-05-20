import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { CheckCircle, XCircle, Loader2, RefreshCcw } from "lucide-react";

import { Button, Card, CardBody, CardHeader, CardTitle, FormField } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { documentTypesApi, documentsApi } from "@/lib/api/index";

const ALLOWED_MIME_TYPES = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

const MAX_FILE_BYTES = 20 * 1024 * 1024; // 20 MB (must match backend setting)

type FileStatus = "idle" | "uploading" | "success" | "error";

type FileItem = {
  file: File;
  status: FileStatus;
  error?: string;
};

function validateFile(file: File): string | null {
  if (!ALLOWED_MIME_TYPES.has(file.type)) {
    return `Tipo no permitido: ${file.type || "desconocido"}. Se aceptan PDF, PNG, JPG y DOCX.`;
  }
  if (file.size > MAX_FILE_BYTES) {
    return `El archivo supera el tamaño máximo (${Math.round(MAX_FILE_BYTES / (1024 * 1024))} MB).`;
  }
  return null;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadDialog({
  supplierId,
  initialDocTypeId,
  initialCoverage,
  onClose,
}: {
  supplierId: number;
  initialDocTypeId?: number | null;
  initialCoverage?: string | null;
  onClose: (uploaded?: boolean) => void;
}) {
  const qc = useQueryClient();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [docTypeId, setDocTypeId] = useState<number | null>(initialDocTypeId ?? null);
  const [coverage, setCoverage] = useState<string>(initialCoverage ?? "");
  const [isUploading, setIsUploading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const {
    data: types,
    isLoading: typesLoading,
    error: typesError,
  } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.list(),
  });
  const activeTypes = (types?.items ?? []).filter((t) => t.active);

  const upload = useMutation({ mutationFn: documentsApi.upload });

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
      prev.map((item) => (item.status === "error" ? { ...item, status: "idle", error: undefined } : item))
    );
    setGlobalError(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const uploadable = files.filter((f) => f.status === "idle");
    if (uploadable.length === 0) {
      setGlobalError("Selecciona al menos un archivo válido para subir.");
      return;
    }
    if (!docTypeId) {
      setGlobalError("Selecciona el tipo de documento.");
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
        const payload: Parameters<typeof documentsApi.upload>[0] = {
          supplier_id: supplierId,
          document_type_id: docTypeId,
          file: item.file,
        };
        if (coverage) payload.coverage_period_start = coverage;
        await upload.mutateAsync(payload);
        setFiles((prev) =>
          prev.map((f) => (f.file === item.file ? { ...f, status: "success" } : f))
        );
        anySuccess = true;
      } catch (e: unknown) {
        let msg = "Error inesperado";
        if (e instanceof ApiError) {
          msg = e.code === "duplicate_file" ? "Archivo duplicado (ya existe)." : e.message;
        }
        setFiles((prev) =>
          prev.map((f) => (f.file === item.file ? { ...f, status: "error", error: msg } : f))
        );
      }
    }

    setIsUploading(false);

    if (anySuccess) {
      qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
      qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] });
    }

    const allDone = files.every((f) => f.status === "success" || (f.status !== "idle" && f.status !== "uploading"));
    const hasFailed = files.some((f) => f.status === "error");

    if (anySuccess && !hasFailed) {
      onClose(true);
    }
    // If there are failures, stay open so the user can see the summary / retry
  }

  const successCount = files.filter((f) => f.status === "success").length;
  const failCount = files.filter((f) => f.status === "error" && !f.error?.startsWith("Tipo") && !f.error?.startsWith("El archivo")).length;
  const preValidationErrors = files.filter((f) => f.status === "error" && (f.error?.startsWith("Tipo") || f.error?.startsWith("El archivo"))).length;
  const hasRetryable = files.some(
    (f) => f.status === "error" && !f.error?.startsWith("Tipo") && !f.error?.startsWith("El archivo")
  );
  const hasAtLeastOneSuccess = successCount > 0;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Subir documento</CardTitle>
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
              <label className="text-sm font-medium text-brand-700" htmlFor="document_type_id">
                Tipo de documento
              </label>
              <select
                id="document_type_id"
                className="mt-1.5 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
                value={docTypeId ?? ""}
                onChange={(e) => setDocTypeId(Number(e.target.value) || null)}
                disabled={typesLoading || activeTypes.length === 0 || isUploading}
                required
              >
                <option value="">
                  {typesLoading
                    ? "Cargando tipos…"
                    : activeTypes.length === 0
                    ? "No hay tipos activos disponibles"
                    : "Selecciona…"}
                </option>
                {activeTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
              {typesError && (
                <p className="mt-1 text-xs text-status-expired">
                  No se pudieron cargar los tipos de documento.
                </p>
              )}
            </div>

            <FormField
              type="date"
              label="Inicio del periodo cubierto"
              hint="Requerido si el tipo tiene vigencia."
              value={coverage}
              onChange={(e) => setCoverage(e.target.value)}
              disabled={isUploading}
            />

            <div>
              <label className="text-sm font-medium text-brand-700" htmlFor="upload-file">
                Archivos
              </label>
              <input
                id="upload-file"
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
              <Button type="button" variant="ghost" onClick={() => onClose(hasAtLeastOneSuccess)} disabled={isUploading}>
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
