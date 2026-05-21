import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, FileStack } from "lucide-react";

import { Badge, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import type { CellStatus, MonthlyRequirement, OneTimeRequirement, ComplianceGrid } from "@/lib/api/index";
import { portalApi } from "@/lib/api/portal";
import { ComplianceGrid as ComplianceGridComponent } from "@/components/suppliers/ComplianceGrid";
import type { ViewerClickParams } from "@/components/suppliers/ComplianceCell";
import { ComplianceSummary } from "@/components/suppliers/ComplianceSummary";
import { OneTimeRequirements } from "@/components/suppliers/OneTimeRequirements";
import { DocumentViewerModal } from "@/components/documents/DocumentViewerModal";

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: CURRENT_YEAR - 2019 }, (_, i) => CURRENT_YEAR - i);

const PORTAL_UPLOADABLE: ReadonlySet<CellStatus> = new Set(["missing", "pending", "expired"]);

// ─── Helpers ─────────────────────────────────────────────────────────────────

function statusTone(status: CellStatus | string | null): BadgeTone {
  switch (status) {
    case "validated":
    case "submitted":     return "valid";
    case "expiring_soon": return "expiring";
    case "expired":
    case "missing":       return "expired";
    case "pending":       return "expiring";
    default:              return "neutral";
  }
}

function statusLabel(status: CellStatus | string | null): string {
  switch (status) {
    case "validated":     return "Validado";
    case "submitted":     return "En validación";
    case "expiring_soon": return "Por vencer";
    case "expired":       return "Vencido";
    case "missing":       return "Faltante";
    case "pending":       return "Pendiente";
    case "future":        return "Futuro";
    case "not_required":  return "No aplica";
    default:              return status ?? "—";
  }
}

function isAlertStatus(s: CellStatus | string | null) {
  return s === "missing" || s === "expired" || s === "pending";
}

function computeCounts(data: ComplianceGrid) {
  let valid = 0, expiring_soon = 0, expired = 0, missing = 0;
  for (const req of data.monthly_requirements) {
    for (const cell of req.cells) {
      if (cell.status === "future" || cell.status === "not_required") continue;
      if (cell.status === "validated" || cell.status === "submitted") valid++;
      else if (cell.status === "expired") expired++;
      else if (cell.status === "missing" || cell.status === "pending") missing++;
    }
  }
  for (const req of data.one_time_requirements) {
    if (req.status === "future" || req.status === "not_required") continue;
    if (req.status === "validated" || req.status === "submitted") valid++;
    else if (req.status === "expired") expired++;
    else if (req.status === "missing" || req.status === "pending") missing++;
  }
  return { valid, expiring_soon, expired, missing };
}

// ─── AlertsSection ────────────────────────────────────────────────────────────

function AlertsSection({
  monthly,
  oneTime,
}: {
  monthly: MonthlyRequirement[];
  oneTime: OneTimeRequirement[];
}) {
  const currentMonth = new Date().getMonth() + 1;

  const monthlyAlerts = monthly.flatMap((req) =>
    req.cells
      .filter((c) => c.month === currentMonth && isAlertStatus(c.status))
      .map((c) => ({ name: req.document_type.name, status: c.status }))
  );
  const oneTimeAlerts = oneTime
    .filter((r) => isAlertStatus(r.status))
    .map((r) => ({ name: r.document_type.name, status: r.status }));

  const alerts = [...monthlyAlerts, ...oneTimeAlerts];

  if (alerts.length === 0) {
    return (
      <div className="mb-6 flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
        <FileStack size={18} className="shrink-0 text-green-600" />
        Toda la documentación del mes está al corriente.
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-900">
        <AlertTriangle size={18} className="shrink-0" />
        Documentos que requieren atención este mes
      </div>
      <ul className="space-y-1.5">
        {alerts.map(({ name, status }, i) => (
          <li
            key={i}
            className="flex items-center justify-between rounded-md bg-white px-3 py-2 text-sm shadow-sm"
          >
            <span className="text-neutral-800">{name}</span>
            <Badge tone={statusTone(status)}>{statusLabel(status)}</Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── PortalPage ──────────────────────────────────────────────────────────────

type OneTimeViewerState = {
  document_type_id: number;
  documentTypeName: string;
  cellStatus: CellStatus;
};

export function PortalPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [oneTimeViewer, setOneTimeViewer] = useState<OneTimeViewerState | null>(null);
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["portal-compliance", year],
    queryFn: () => portalApi.getCompliance(year),
  });

  function handleOneTimeViewerClick({ document_type_id }: ViewerClickParams) {
    const item = data?.one_time_requirements.find(r => r.document_type.id === document_type_id);
    if (!item) return;
    setOneTimeViewer({
      document_type_id,
      documentTypeName: item.document_type.name,
      cellStatus: item.status,
    });
  }

  function handleInvalidate() {
    qc.invalidateQueries({ queryKey: ["portal-compliance", year] });
  }

  if (isLoading) return <p className="p-8 text-sm text-neutral-500">Cargando…</p>;
  if (isError || !data)
    return <p className="p-8 text-sm text-red-600">No fue posible cargar la información. Intenta de nuevo.</p>;

  const counts = computeCounts(data);
  const bothEmpty =
    data.monthly_requirements.length === 0 && data.one_time_requirements.length === 0;

  return (
    <>
    <div className="mx-auto max-w-6xl p-8">
      {/* Header */}
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-neutral-500">Portal del proveedor</p>
          <h1 className="text-2xl font-semibold text-brand-700">{data.supplier.legal_name}</h1>
          <p className="font-mono text-sm uppercase text-neutral-500">{data.supplier.rfc}</p>
          <p className="mt-1 text-sm text-neutral-600">
            Tipo: <span className="font-medium">{data.supplier.supplier_type.name}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-neutral-600">Año:</label>
          <select
            className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </header>

      {/* Tarjeta de cumplimiento */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Cumplimiento {year}</CardTitle>
        </CardHeader>
        <CardBody>
          <ComplianceSummary percent={data.supplier.compliance_percent} counts={counts} />
        </CardBody>
      </Card>

      {/* Alertas del mes */}
      <AlertsSection
        monthly={data.monthly_requirements}
        oneTime={data.one_time_requirements}
      />

      {bothEmpty ? (
        <div className="rounded border border-dashed border-neutral-300 bg-neutral-50 p-8 text-center text-sm text-neutral-600">
          No tienes requisitos de documentación configurados.
        </div>
      ) : (
        <>
          {/* Documentos periódicos */}
          {data.monthly_requirements.length > 0 && (
            <section className="mb-6">
              <div className="mb-3 flex items-baseline justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
                  Documentos periódicos
                </h2>
              </div>
              <ComplianceGridComponent
                data={data}
                readOnly
                portalMode
                onSubmitted={handleInvalidate}
                uploadFn={(file, dtId, period) =>
                  portalApi.upload(file, dtId, period ?? undefined).then(() => {})
                }
              />
            </section>
          )}

          {/* Documentos únicos */}
          {data.one_time_requirements.length > 0 && (
            <OneTimeRequirements
              items={data.one_time_requirements}
              onViewerClick={handleOneTimeViewerClick}
            />
          )}
        </>
      )}
    </div>

    {/* Viewer para requisitos únicos (one-time) */}
    {oneTimeViewer && data && (
      <DocumentViewerModal
        supplierId={data.supplier.id}
        documentTypeId={oneTimeViewer.document_type_id}
        documentTypeName={oneTimeViewer.documentTypeName}
        coveragePeriodStart={null}
        canAddDocuments={PORTAL_UPLOADABLE.has(oneTimeViewer.cellStatus)}
        canValidateType={false}
        canSubmit={PORTAL_UPLOADABLE.has(oneTimeViewer.cellStatus)}
        uploadFn={(file) =>
          portalApi.upload(file, oneTimeViewer.document_type_id, undefined).then(() => {})
        }
        {...(PORTAL_UPLOADABLE.has(oneTimeViewer.cellStatus)
          ? { onSubmitted: () => { handleInvalidate(); setOneTimeViewer(null); } }
          : {})}
        onClose={() => setOneTimeViewer(null)}
      />
    )}
    </>
  );
}
