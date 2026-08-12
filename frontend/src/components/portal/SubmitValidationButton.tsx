import { useState } from "react";
import { Send, Loader2, CheckCircle, XCircle } from "lucide-react";

import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { portalApi } from "@/lib/api/portal";

function apiErrorMessage(e: ApiError): string {
  const code = (e.details?.code as string | undefined) ?? e.code;
  switch (code) {
    case "no_documents_uploaded":
      return "Debes cargar al menos un documento antes de enviar a validación.";
    case "already_submitted":
      return "Ya existe un envío pendiente para este tipo y período.";
    case "cell_not_submittable":
      return "Este documento ya está validado o vigente; no necesita ser enviado.";
    case "supplier_not_linked":
      return "Tu cuenta no está vinculada a ningún proveedor. Contacta al administrador.";
    default:
      return e.message || "Error inesperado al enviar a validación.";
  }
}

type Props = {
  documentTypeId: number;
  documentTypeName: string;
  coveragePeriodStart: string | null;
  onSubmitted: () => void;
};

export function SubmitValidationButton({
  documentTypeId,
  documentTypeName,
  coveragePeriodStart,
  onSubmitted,
}: Props) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleConfirm() {
    setIsSubmitting(true);
    setError(null);
    try {
      await portalApi.submit(documentTypeId, coveragePeriodStart);
      setSubmitted(true);
      setShowConfirm(false);
      onSubmitted();
    } catch (e: unknown) {
      setError(e instanceof ApiError ? apiErrorMessage(e) : "Error inesperado.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700">
        <CheckCircle size={13} className="shrink-0" />
        En validación
      </span>
    );
  }

  return (
    <>
      <Button
        size="sm"
        variant="primary"
        className="bg-emerald-600 hover:bg-emerald-700 focus-visible:ring-emerald-500"
        onClick={() => { setError(null); setShowConfirm(true); }}
      >
        <Send size={14} className="mr-1.5 shrink-0" />
        Enviar a validar
      </Button>

      {showConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-6 shadow-lg">
            <h3 className="text-base font-semibold text-neutral-900">
              ¿Enviar a validación?
            </h3>
            <p className="mt-2 text-sm text-neutral-600">
              Se enviará el paquete de{" "}
              <span className="font-medium">{documentTypeName}</span>{" "}
              {coveragePeriodStart
                ? `del período ${new Date(coveragePeriodStart + "T00:00:00").toLocaleDateString("es-MX", { year: "numeric", month: "long" })} `
                : ""}
              a revisión de contabilidad. El botón quedará inhabilitado hasta que contabilidad procese la solicitud.
            </p>

            {error && (
              <div className="mt-3 flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                <XCircle size={15} className="mt-0.5 shrink-0" />
                {error}
              </div>
            )}

            <div className="mt-5 flex justify-end gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowConfirm(false)}
                disabled={isSubmitting}
              >
                Cancelar
              </Button>
              <Button
                size="sm"
                variant="primary"
                className="bg-emerald-600 hover:bg-emerald-700"
                onClick={handleConfirm}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 size={14} className="animate-spin" />
                    Enviando…
                  </span>
                ) : (
                  "Confirmar envío"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
