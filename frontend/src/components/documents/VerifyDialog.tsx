import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { documentsApi, type DocumentOut } from "@/lib/api/index";

export function VerifyDialog({
  document,
  supplierId,
  onClose,
}: {
  document: DocumentOut;
  supplierId: number;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const verify = useMutation({
    mutationFn: () => documentsApi.verify(document.id, note || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
      qc.invalidateQueries({ queryKey: ["document", document.id] });
      onClose();
    },
    onError: (e: unknown) => {
      setError(e instanceof ApiError ? e.message : "Error inesperado al verificar.");
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Marcar como verificado</CardTitle>
        </CardHeader>
        <CardBody>
          {error && (
            <p className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">
              {error}
            </p>
          )}
          <p className="mb-4 text-sm text-neutral-600">
            Estás marcando como <span className="font-medium text-brand-700">verificado</span> el
            documento{" "}
            <span className="font-medium">
              {document.file.name}
            </span>
            . Esta acción queda registrada en el historial de auditoría.
          </p>
          <div className="mb-4">
            <label className="text-sm font-medium text-brand-700" htmlFor="verify-note">
              Nota de verificación{" "}
              <span className="text-xs font-normal text-neutral-400">(opcional)</span>
            </label>
            <textarea
              id="verify-note"
              className="mt-1.5 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
              rows={3}
              placeholder="Ej. Cotejado con portal del SAT el 2026-05-18"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={verify.isPending}
              onClick={() => verify.mutate()}
            >
              {verify.isPending ? "Verificando…" : "Confirmar verificación"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
