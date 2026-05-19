import type { ComplianceGrid as ComplianceGridData } from "@/lib/api/index";

import { COMPLIANCE_LEGEND, ComplianceCell, type UploadClickParams } from "./ComplianceCell";
import type { CellStatus } from "@/lib/api/index";

const MONTH_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

type ComplianceGridProps = {
  data: ComplianceGridData;
  onDocumentClick?: (documentId: number) => void;
  onUploadClick?: (params: UploadClickParams) => void;
};

export function ComplianceGrid({ data, onDocumentClick, onUploadClick }: ComplianceGridProps) {
  if (data.monthly_requirements.length === 0) {
    return (
      <div className="rounded border border-dashed border-neutral-300 bg-neutral-50 p-6 text-sm text-neutral-600">
        Este proveedor no tiene tipos de documento con periodicidad mensual configurados.
      </div>
    );
  }

  const todayIsThisYear = new Date().getFullYear() === data.year;
  const currentMonth = todayIsThisYear ? new Date().getMonth() + 1 : null;

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded border border-neutral-200 bg-white">
        <div
          className="grid min-w-[720px] text-sm"
          style={{
            gridTemplateColumns: "minmax(180px,1fr) repeat(12, minmax(40px, 1fr))",
          }}
          role="table"
          aria-label={`Cumplimiento mensual ${data.year}`}
        >
          <div
            className="sticky top-0 z-10 border-b border-neutral-200 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wide text-neutral-500"
            role="columnheader"
          >
            Tipo de documento
          </div>
          {MONTH_LABELS.map((label, idx) => {
            const month = idx + 1;
            const isCurrent = currentMonth === month;
            return (
              <div
                key={label}
                className={`sticky top-0 z-10 border-b border-neutral-200 px-1 py-2 text-center text-xs font-semibold uppercase tracking-wide ${
                  isCurrent ? "bg-brand-50 text-brand-700" : "bg-white text-neutral-500"
                }`}
                role="columnheader"
                aria-label={`Mes ${month}`}
              >
                {label}
              </div>
            );
          })}

          {data.monthly_requirements.map((req) => (
            <div key={req.document_type.id} className="contents" role="row">
              <div
                className="flex items-center border-t border-neutral-100 px-3 py-2 text-neutral-800"
                role="rowheader"
                title={req.document_type.name}
              >
                <span className="truncate">{req.document_type.name}</span>
              </div>
              {req.cells.map((cell) => {
                const isCurrent = currentMonth === cell.month;
                return (
                  <div
                    key={`${req.document_type.id}-${cell.month}`}
                    className={`flex items-center justify-center border-t border-neutral-100 py-2 ${
                      isCurrent ? "bg-brand-50/40" : ""
                    }`}
                    role="cell"
                  >
                    <ComplianceCell
                      status={cell.status}
                      month={cell.month}
                      document_id={cell.document_id}
                      document_type_id={req.document_type.id}
                      coverage_period_start={cell.coverage_period_start}
                      onDocumentClick={onDocumentClick}
                      onUploadClick={onUploadClick}
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <ComplianceLegend />
    </div>
  );
}

function ComplianceLegend() {
  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">
        Leyenda
      </p>
      <ul className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs text-neutral-600 sm:grid-cols-3 lg:grid-cols-4">
        {COMPLIANCE_LEGEND.map((item) => (
          <li key={item.status} className="flex items-center gap-2">
            <LegendSwatch status={item.status} />
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function LegendSwatch({ status }: { status: CellStatus }) {
  if (status === "not_required") {
    return (
      <span className="inline-block h-3 w-3 shrink-0 rounded-full border border-dashed border-neutral-300 bg-neutral-100" />
    );
  }
  return <ComplianceCell status={status} size="sm" />;
}
