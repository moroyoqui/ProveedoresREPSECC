import { AlertOctagon } from "lucide-react";

type Props = {
  reason: string;
  rejectedAt?: string | null;
};

export function RejectionReasonBanner({ reason, rejectedAt }: Props) {
  const dateLabel = rejectedAt
    ? new Date(rejectedAt).toLocaleDateString("es-MX", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <AlertOctagon size={18} className="mt-0.5 shrink-0 text-red-500" />
      <div className="min-w-0">
        <p className="font-semibold">
          Envío rechazado por contabilidad
          {dateLabel && (
            <span className="ml-2 font-normal text-red-600 text-xs">({dateLabel})</span>
          )}
        </p>
        <p className="mt-0.5 text-red-700">{reason}</p>
      </div>
    </div>
  );
}
