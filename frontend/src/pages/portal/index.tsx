import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ChevronDown, ChevronRight, Clock, FileStack } from "lucide-react";

import { Badge } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import type { CellStatus, OneTimeRequirement, MonthlyRequirement } from "@/lib/api/index";
import { portalApi, type DocumentHistoryItem } from "@/lib/api/portal";

const MONTH_LABELS = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: CURRENT_YEAR - 2019 }, (_, i) => CURRENT_YEAR - i);

function statusTone(status: CellStatus | string | null): BadgeTone {
  switch (status) {
    case "validated": return "valid";
    case "submitted": return "valid";
    case "expiring_soon": return "expiring";
    case "expired": return "expired";
    case "missing": return "expired";
    case "pending": return "expiring";
    default: return "neutral";
  }
}

function statusLabel(status: CellStatus | string | null): string {
  switch (status) {
    case "validated": return "Validado";
    case "submitted": return "Enviado";
    case "expiring_soon": return "Por vencer";
    case "expired": return "Vencido";
    case "missing": return "Faltante";
    case "pending": return "Pendiente";
    case "future": return "Futuro";
    case "not_required": return "No aplica";
    default: return status ?? "—";
  }
}

function isAlertStatus(status: CellStatus | string | null): boolean {
  return status === "missing" || status === "expired" || status === "pending";
}

function AlertsSection({
  monthly,
  oneTime,
  onTypeClick,
}: {
  monthly: MonthlyRequirement[];
  oneTime: OneTimeRequirement[];
  onTypeClick: (id: number) => void;
}) {
  const currentMonth = new Date().getMonth() + 1;

  const monthlyAlerts = monthly.flatMap((req) =>
    req.cells
      .filter((cell) => cell.month === currentMonth && isAlertStatus(cell.status))
      .map((cell) => ({ req, cell }))
  );
  const oneTimeAlerts = oneTime.filter((r) => isAlertStatus(r.status));

  if (monthlyAlerts.length === 0 && oneTimeAlerts.length === 0) {
    return (
      <div className="mb-6 flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
        <FileStack size={18} className="shrink-0 text-green-600" />
        <span>Toda la documentación del mes está al corriente.</span>
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-900">
        <AlertTriangle size={18} className="shrink-0" />
        Documentos que requieren atención
      </div>
      <ul className="space-y-2">
        {monthlyAlerts.map(({ req, cell }) => (
          <li
            key={`m-${req.document_type.id}`}
            className="flex cursor-pointer items-center justify-between rounded-md bg-white px-3 py-2 text-sm shadow-sm hover:bg-amber-50"
            onClick={() => onTypeClick(req.document_type.id)}
          >
            <span className="text-neutral-800">{req.document_type.name}</span>
            <Badge tone={statusTone(cell.status)}>{statusLabel(cell.status)}</Badge>
          </li>
        ))}
        {oneTimeAlerts.map((req) => (
          <li
            key={`ot-${req.document_type.id}`}
            className="flex cursor-pointer items-center justify-between rounded-md bg-white px-3 py-2 text-sm shadow-sm hover:bg-amber-50"
            onClick={() => onTypeClick(req.document_type.id)}
          >
            <span className="text-neutral-800">{req.document_type.name}</span>
            <Badge tone={statusTone(req.status)}>{statusLabel(req.status)}</Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}

function HistoryPanel({
  documentTypeId,
  documentTypeName,
}: {
  documentTypeId: number;
  documentTypeName: string;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["portal-history", documentTypeId],
    queryFn: () => portalApi.getDocumentHistory(documentTypeId),
  });

  return (
    <div className="border-t border-neutral-200 bg-neutral-50 px-4 py-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Historial — {documentTypeName}
      </p>
      {isLoading && <p className="text-sm text-neutral-500">Cargando…</p>}
      {data && data.length === 0 && (
        <p className="text-sm text-neutral-500">Sin entregas registradas.</p>
      )}
      {data && data.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-neutral-500">
              <th className="pb-1 pr-4 font-medium">Período</th>
              <th className="pb-1 pr-4 font-medium">Archivo</th>
              <th className="pb-1 pr-4 font-medium">Estado</th>
              <th className="pb-1 font-medium">Versión</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item: DocumentHistoryItem) => (
              <tr key={item.id} className="border-t border-neutral-200">
                <td className="py-1 pr-4 text-neutral-700">
                  {item.coverage_period_start
                    ? new Date(item.coverage_period_start + "T00:00:00").toLocaleDateString("es-MX", {
                        month: "short",
                        year: "numeric",
                      })
                    : "—"}
                </td>
                <td className="py-1 pr-4 text-neutral-700 max-w-xs truncate">
                  {item.file_name_original}
                </td>
                <td className="py-1 pr-4">
                  <Badge tone={statusTone(item.status)}>{statusLabel(item.status)}</Badge>
                </td>
                <td className="py-1 text-neutral-500">v{item.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function PortalPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [selectedDocType, setSelectedDocType] = useState<number | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["portal-compliance", year],
    queryFn: () => portalApi.getCompliance(year),
  });

  function handleTypeClick(id: number) {
    setSelectedDocType((prev) => (prev === id ? null : id));
  }

  return (
    <div className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-brand-700">Mi documentación</h1>
          {data && (
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-neutral-600">
              <span className="font-medium text-neutral-800">{data.supplier.legal_name}</span>
              <span className="text-neutral-400">·</span>
              <span>{data.supplier.rfc}</span>
              <span className="text-neutral-400">·</span>
              <span>{data.supplier.supplier_type.name}</span>
              <span className="text-neutral-400">·</span>
              <Badge tone={data.supplier.compliance_percent >= 80 ? "valid" : "expiring"}>
                {data.supplier.compliance_percent}% cumplimiento
              </Badge>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-neutral-600">Año:</label>
          <select
            className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
      </header>

      {isLoading && (
        <p className="text-sm text-neutral-500">Cargando documentación…</p>
      )}
      {isError && (
        <p className="text-sm text-status-expired">
          No fue posible cargar la información. Intenta de nuevo.
        </p>
      )}

      {data && (
        <>
          <AlertsSection
            monthly={data.monthly_requirements}
            oneTime={data.one_time_requirements}
            onTypeClick={handleTypeClick}
          />

          {/* Grid mensual */}
          {data.monthly_requirements.length > 0 && (
            <section className="mb-6">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                Documentos periódicos
              </h2>
              <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
                <table className="min-w-[760px] w-full text-sm">
                  <thead>
                    <tr>
                      <th className="border-b border-neutral-200 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                        Tipo de documento
                      </th>
                      {MONTH_LABELS.map((m, i) => {
                        const isCurrentMonth =
                          year === CURRENT_YEAR && new Date().getMonth() === i;
                        return (
                          <th
                            key={m}
                            className={`border-b border-neutral-200 px-1 py-2 text-center text-xs font-semibold uppercase tracking-wide ${
                              isCurrentMonth ? "bg-brand-50 text-brand-700" : "text-neutral-500"
                            }`}
                          >
                            {m}
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {data.monthly_requirements.map((req) => (
                      <tr key={req.document_type.id}>
                        <td colSpan={13} className="p-0">
                          <table className="w-full text-sm">
                            <tbody>
                              <tr
                                className="cursor-pointer border-t border-neutral-100 hover:bg-neutral-50"
                                onClick={() => handleTypeClick(req.document_type.id)}
                              >
                                <td
                                  className="flex items-center gap-1 px-3 py-2 font-medium text-neutral-800"
                                  style={{ minWidth: "180px" }}
                                >
                                  {selectedDocType === req.document_type.id ? (
                                    <ChevronDown size={14} className="shrink-0 text-neutral-400" />
                                  ) : (
                                    <ChevronRight size={14} className="shrink-0 text-neutral-400" />
                                  )}
                                  {req.document_type.name}
                                </td>
                                {req.cells.map((cell) => (
                                  <td key={cell.month} className="px-1 py-2 text-center">
                                    <span
                                      className={`inline-block h-5 w-5 rounded-sm ${cellBg(cell.status)}`}
                                      title={statusLabel(cell.status)}
                                    />
                                  </td>
                                ))}
                              </tr>
                            </tbody>
                          </table>
                          {selectedDocType === req.document_type.id && (
                            <HistoryPanel
                              documentTypeId={req.document_type.id}
                              documentTypeName={req.document_type.name}
                            />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Documentos únicos */}
          {data.one_time_requirements.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
                Documentos únicos
              </h2>
              <div className="rounded-lg border border-neutral-200 bg-white">
                {data.one_time_requirements.map((req) => (
                  <div key={req.document_type.id}>
                    <div
                      className="flex cursor-pointer items-center justify-between border-t border-neutral-100 px-4 py-3 first:border-t-0 hover:bg-neutral-50"
                      onClick={() => handleTypeClick(req.document_type.id)}
                    >
                      <div className="flex items-center gap-2 text-sm font-medium text-neutral-800">
                        {selectedDocType === req.document_type.id ? (
                          <ChevronDown size={14} className="text-neutral-400" />
                        ) : (
                          <ChevronRight size={14} className="text-neutral-400" />
                        )}
                        {req.document_type.name}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-neutral-500">
                        {req.due_date_effective && (
                          <span className="flex items-center gap-1">
                            <Clock size={13} />
                            {new Date(req.due_date_effective + "T00:00:00").toLocaleDateString(
                              "es-MX"
                            )}
                          </span>
                        )}
                        <Badge tone={statusTone(req.status)}>{statusLabel(req.status)}</Badge>
                      </div>
                    </div>
                    {selectedDocType === req.document_type.id && (
                      <div className="border-t border-neutral-100">
                        <HistoryPanel
                          documentTypeId={req.document_type.id}
                          documentTypeName={req.document_type.name}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function cellBg(status: CellStatus): string {
  switch (status) {
    case "validated": return "bg-status-valid";
    case "submitted": return "bg-status-valid";
    case "expiring_soon": return "bg-status-expiring";
    case "expired": return "bg-status-expired";
    case "missing": return "bg-status-missing";
    case "pending": return "bg-status-expiring opacity-60";
    case "future": return "bg-neutral-200";
    case "not_required": return "bg-neutral-100";
    default: return "bg-neutral-200";
  }
}
