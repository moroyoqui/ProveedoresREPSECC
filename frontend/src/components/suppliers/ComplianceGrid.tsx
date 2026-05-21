import { useState } from "react";
import type { ComplianceGrid as ComplianceGridData } from "@/lib/api/index";

import { COMPLIANCE_LEGEND, ComplianceCell, type UploadClickParams, type ViewerClickParams } from "./ComplianceCell";
import { DocumentViewerModal } from "@/components/documents/DocumentViewerModal";
import type { CellStatus } from "@/lib/api/index";

const PORTAL_UPLOADABLE: ReadonlySet<CellStatus> = new Set(["missing", "pending", "expired"]);

const MONTH_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

type ViewerState = ViewerClickParams & {
  documentTypeName: string;
  cellStatus: CellStatus;
  typeValidated: boolean;
};

type ComplianceGridProps = {
  data: ComplianceGridData;
  readOnly?: boolean;
  onUploadClick?: (params: UploadClickParams) => void;
  portalMode?: boolean;
};

export function ComplianceGrid({ data, readOnly = false, onUploadClick, portalMode = false }: ComplianceGridProps) {
  const [viewerState, setViewerState] = useState<ViewerState | null>(null);
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

          {data.monthly_requirements.map((req) => {
            const isBimonthly = req.document_type.periodicity === "bimonthly";

            const rowHeader = (
              <div
                className="flex items-start border-t border-neutral-100 px-3 py-2 text-neutral-800"
                role="rowheader"
              >
                <span className="break-words leading-snug">{req.document_type.name}</span>
              </div>
            );

            if (isBimonthly) {
              // Bimonthly: period starts on odd month S, due the following month
              // (S+2). E.g. Jan-Feb period is due in March.
              // Nov-Dec (S=11) would be due Jan next year → capped at col 12.
              const dueColMap = new Map<number, (typeof req.cells)[number]>();
              for (const cell of req.cells) {
                if (cell.status === "not_required") continue;
                const dueCol = ((cell.month + 1) % 12) + 1; // wraps 13→1 for Nov-Dec period
                dueColMap.set(dueCol, cell);
              }
              return (
                <div key={req.document_type.id} className="contents" role="row">
                  {rowHeader}
                  {Array.from({ length: 12 }, (_, i) => {
                    const col = i + 1;
                    const cell = dueColMap.get(col);
                    const isCurrent =
                      cell != null &&
                      currentMonth != null &&
                      currentMonth >= cell.month &&
                      currentMonth <= cell.month + 2;
                    return (
                      <div
                        key={`${req.document_type.id}-${col}`}
                        className={`flex items-center justify-center border-t border-neutral-100 py-2 ${
                          isCurrent ? "bg-brand-50/40" : ""
                        }`}
                        role="cell"
                      >
                        {cell && (
                          <ComplianceCell
                            status={cell.status}
                            month={col}
                            document_id={cell.document_id}
                            document_count={cell.document_count}
                            document_type_id={req.document_type.id}
                            coverage_period_start={
                              cell.coverage_period_start
                                ? String(cell.coverage_period_start)
                                : null
                            }
                            onViewerClick={
                              portalMode && PORTAL_UPLOADABLE.has(cell.status)
                                ? undefined
                                : (params) =>
                                    setViewerState({ ...params, documentTypeName: req.document_type.name, cellStatus: cell.status, typeValidated: cell.type_validated ?? false })
                            }
                            onUploadClick={onUploadClick}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            }

            return (
              <div key={req.document_type.id} className="contents" role="row">
                {rowHeader}
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
                        document_count={cell.document_count}
                        document_type_id={req.document_type.id}
                        coverage_period_start={
                          cell.coverage_period_start
                            ? String(cell.coverage_period_start)
                            : null
                        }
                        onViewerClick={
                          portalMode && PORTAL_UPLOADABLE.has(cell.status)
                            ? undefined
                            : (params) =>
                                setViewerState({ ...params, documentTypeName: req.document_type.name, cellStatus: cell.status, typeValidated: cell.type_validated ?? false })
                        }
                        onUploadClick={onUploadClick}
                      />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      <ComplianceLegend />

      {viewerState && (
        <DocumentViewerModal
          supplierId={data.supplier.id}
          documentTypeId={viewerState.document_type_id}
          documentTypeName={viewerState.documentTypeName}
          coveragePeriodStart={viewerState.coverage_period_start}
          canAddDocuments={!readOnly && !viewerState.typeValidated && viewerState.cellStatus !== "not_required"}
          typeValidated={viewerState.typeValidated}
          canValidateType={!readOnly && !viewerState.typeValidated && viewerState.cellStatus !== "not_required"}
          onClose={() => setViewerState(null)}
        />
      )}
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
  return <ComplianceCell status={status} size="sm" />;
}
