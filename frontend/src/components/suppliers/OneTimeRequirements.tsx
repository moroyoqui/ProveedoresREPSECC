import { ExternalLink, Upload } from "lucide-react";

import type { OneTimeRequirement } from "@/lib/api/index";
import { Button } from "@/components/ui";
import { ComplianceCell, type UploadClickParams } from "./ComplianceCell";

function fmt(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

type OneTimeRequirementsProps = {
  items: OneTimeRequirement[];
  onDocumentClick?: (documentId: number) => void;
  onUploadClick?: (params: UploadClickParams) => void;
};

export function OneTimeRequirements({ items, onDocumentClick, onUploadClick }: OneTimeRequirementsProps) {
  if (items.length === 0) return null;

  return (
    <section className="mb-6">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
        Documentos sin periodicidad
      </h2>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <li
            key={item.document_type.id}
            className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white px-4 py-3"
          >
            <ComplianceCell
              status={item.status}
              document_id={item.document_id}
              document_type_id={item.document_type.id}
              coverage_period_start={null}
              onDocumentClick={onDocumentClick}
              onUploadClick={onUploadClick}
            />

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-neutral-800">
                {item.document_type.name}
              </p>
              {item.due_date_effective && (
                <p className="text-xs text-neutral-500">
                  Vence: {fmt(item.due_date_effective)}
                </p>
              )}
            </div>

            {item.document_id != null && onDocumentClick ? (
              <Button
                variant="ghost"
                className="shrink-0 px-2 py-1 text-xs"
                onClick={() => onDocumentClick(item.document_id!)}
                title="Ver documento"
              >
                <ExternalLink size={14} />
                Ver
              </Button>
            ) : item.document_id == null && onUploadClick ? (
              <Button
                variant="ghost"
                className="shrink-0 px-2 py-1 text-xs"
                onClick={() =>
                  onUploadClick({ document_type_id: item.document_type.id, coverage_period_start: null })
                }
                title="Subir documento"
              >
                <Upload size={14} />
                Subir
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
