import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import type { CellStatus } from "@/lib/api/index";
import { portalApi } from "@/lib/api/portal";
import { ComplianceGrid as ComplianceGridComponent } from "@/components/suppliers/ComplianceGrid";
import type { ViewerClickParams } from "@/components/suppliers/ComplianceCell";
import { ComplianceSummary } from "@/components/suppliers/ComplianceSummary";
import { OneTimeRequirements } from "@/components/suppliers/OneTimeRequirements";
import { PortalDocumentViewerModal } from "@/components/portal/PortalDocumentViewerModal";
import {
  CURRENT_YEAR,
  YEAR_OPTIONS,
  computeCounts,
} from "./shared";

/**
 * Pantalla de CONSULTA del portal del proveedor (spec 013, US1).
 * Estrictamente de solo lectura (FR-002): sin controles de carga ni envío a
 * validación. Los elementos elegibles ofrecen "Ir a cargar" que navega a la
 * pantalla de Carga con el contexto preseleccionado (US2, FR-004).
 */

type OneTimeViewerState = {
  document_type_id: number;
  documentTypeName: string;
  cellStatus: CellStatus;
};

export function PortalConsultaPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [oneTimeViewer, setOneTimeViewer] = useState<OneTimeViewerState | null>(null);

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
          <p className="text-xs uppercase tracking-wide text-neutral-500">Consulta de documentación</p>
          <h1 className="text-2xl font-semibold text-brand-700">{data.supplier.legal_name}</h1>
          <p className="font-mono text-sm uppercase text-neutral-500">{data.supplier.rfc}</p>
          <p className="mt-1 text-sm text-neutral-600">
            Tipo: <span className="font-medium">{data.supplier.supplier_type.name}</span>
          </p>
          <p className="mt-0.5 text-sm text-neutral-600">
            Sector:{" "}
            <span className="font-medium">
              {data.sector ? data.sector.name : <span className="italic text-neutral-400">Sin clasificar</span>}
            </span>
            {data.giro && (
              <>
                {" · "}Giro: <span className="font-medium">{data.giro.name}</span>
              </>
            )}
          </p>
          {data.repse_folio && (
            <p className="mt-0.5 text-sm text-neutral-600">
              Folio REPSE:{" "}
              <span className="font-mono font-medium">{data.repse_folio}</span>
            </p>
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

      {bothEmpty ? (
        <div className="rounded border border-dashed border-neutral-300 bg-neutral-50 p-8 text-center text-sm text-neutral-600">
          No tienes requisitos de documentación configurados.
        </div>
      ) : (
        <>
          {/* Documentos periódicos — grid de solo lectura */}
          {data.monthly_requirements.length > 0 && (
            <section className="mb-6">
              <div className="mb-3 flex items-baseline justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
                  Documentos periódicos
                </h2>
              </div>
              <ComplianceGridComponent data={data} readOnly portalMode />
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

    {/* Viewer de solo lectura para requisitos únicos */}
    {oneTimeViewer && data && (
      <PortalDocumentViewerModal
        supplierId={data.supplier.id}
        documentTypeId={oneTimeViewer.document_type_id}
        documentTypeName={oneTimeViewer.documentTypeName}
        coveragePeriodStart={null}
        canAddDocuments={false}
        canSubmit={false}
        onClose={() => setOneTimeViewer(null)}
      />
    )}
    </>
  );
}
