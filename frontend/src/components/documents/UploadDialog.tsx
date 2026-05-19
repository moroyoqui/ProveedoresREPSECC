import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, CardBody, CardHeader, CardTitle, FormField } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { documentTypesApi, documentsApi } from "@/lib/api/index";

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
  const [file, setFile] = useState<File | null>(null);
  const [docTypeId, setDocTypeId] = useState<number | null>(initialDocTypeId ?? null);
  const [coverage, setCoverage] = useState<string>(initialCoverage ?? "");
  const [error, setError] = useState<string | null>(null);

  const {
    data: types,
    isLoading: typesLoading,
    error: typesError,
  } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.list(),
  });
  const activeTypes = (types?.items ?? []).filter((t) => t.active);

  const upload = useMutation({
    mutationFn: documentsApi.upload,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
      qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] });
      onClose(true);
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError) {
        if (e.code === "duplicate_file") {
          setError("Este archivo ya fue cargado previamente para tu organización.");
        } else {
          setError(e.message);
        }
      } else {
        setError("Error inesperado");
      }
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !docTypeId) {
      setError("Selecciona archivo y tipo de documento");
      return;
    }
    setError(null);
    const payload: Parameters<typeof documentsApi.upload>[0] = {
      supplier_id: supplierId,
      document_type_id: docTypeId,
      file,
    };
    if (coverage) payload.coverage_period_start = coverage;
    upload.mutate(payload);
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Subir documento</CardTitle>
        </CardHeader>
        <CardBody>
          {error && (
            <p className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">
              {error}
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
                disabled={typesLoading || activeTypes.length === 0}
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
                  No se pudieron cargar los tipos de documento. Refresca la página o vuelve a
                  iniciar sesión.
                </p>
              )}
              {!typesLoading && !typesError && activeTypes.length === 0 && (
                <p className="mt-1 text-xs text-neutral-500">
                  Activa tipos canónicos o crea uno personalizado en Configuración → Tipos de
                  documento.
                </p>
              )}
            </div>
            <FormField
              type="date"
              label="Inicio del periodo cubierto"
              hint="Requerido si el tipo tiene vigencia."
              value={coverage}
              onChange={(e) => setCoverage(e.target.value)}
            />
            <div>
              <label className="text-sm font-medium text-brand-700" htmlFor="upload-file">
                Archivo
              </label>
              <input
                id="upload-file"
                type="file"
                accept="application/pdf,image/png,image/jpeg"
                className="mt-1.5 block w-full text-sm"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                required
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="ghost" onClick={() => onClose(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={upload.isPending}>
                {upload.isPending ? "Subiendo…" : "Subir"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
