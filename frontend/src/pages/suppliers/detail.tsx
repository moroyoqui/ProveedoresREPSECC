import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { Pencil, Upload } from "lucide-react";

import { documentsApi, suppliersApi } from "@/lib/api/index";
import type { UploadClickParams } from "@/components/suppliers/ComplianceCell";
import { Button, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { UploadDialog } from "@/components/documents/UploadDialog";
import { ComplianceGrid } from "@/components/suppliers/ComplianceGrid";
import { OneTimeRequirements } from "@/components/suppliers/OneTimeRequirements";

export function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>();
  const supplierId = Number(id);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadPreset, setUploadPreset] = useState<{
    document_type_id?: number | null;
    coverage_period_start?: string | null;
  }>({});
  const year = new Date().getFullYear();

  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["supplier", supplierId],
    queryFn: () => suppliersApi.detail(supplierId),
    enabled: !Number.isNaN(supplierId),
  });

  const compliance = useQuery({
    queryKey: ["supplier-compliance", supplierId, year],
    queryFn: () => suppliersApi.compliance(supplierId, year),
    enabled: !Number.isNaN(supplierId),
  });

  async function handleDocumentClick(documentId: number) {
    try {
      const { token } = await documentsApi.downloadToken(documentId);
      window.open(`/api/v1/files/${token}`, "_blank", "noopener,noreferrer");
    } catch {
      // si falla silenciosamente, el usuario puede reintentar desde el listado
    }
  }

  function handleUploadClick(params: UploadClickParams) {
    setUploadPreset(params);
    setShowUpload(true);
  }

  function handleUploadClose() {
    setShowUpload(false);
    setUploadPreset({});
    qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
    qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] });
  }

  if (isLoading) return <p className="p-8 text-sm text-neutral-500">Cargando…</p>;
  if (!data) return <p className="p-8 text-sm text-status-expired">No encontrado</p>;

  const complianceData = compliance.data;
  const bothEmpty =
    complianceData &&
    complianceData.monthly_requirements.length === 0 &&
    complianceData.one_time_requirements.length === 0;

  return (
    <div className="mx-auto max-w-6xl p-8">
      <Link to="/suppliers" className="text-sm text-brand-500 hover:underline">
        ← Volver a proveedores
      </Link>

      <header className="mt-3 mb-6 flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-neutral-500">Proveedor</p>
          <h1 className="text-2xl font-semibold text-brand-700">{data.legal_name}</h1>
          <p className="font-mono text-sm uppercase text-neutral-500">{data.rfc}</p>
          <p className="mt-1 text-sm text-neutral-600">
            Tipo: <span className="font-medium">{data.supplier_type.name}</span>
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
          <p className="mt-0.5 text-sm text-neutral-600">
            Contacto:{" "}
            <span className="font-medium">
              {data.contact_name ?? <span className="italic text-neutral-400">—</span>}
            </span>
            {data.contact_email && <> · {data.contact_email}</>}
            {data.contact_phone && <> · {data.contact_phone}</>}
          </p>
          {data.repse_folio && (
            <p className="mt-0.5 text-sm text-neutral-600">
              Folio REPSE:{" "}
              <span className="font-mono font-medium">{data.repse_folio}</span>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Link to={`/suppliers/${data.id}/edit`}>
            <Button variant="secondary" data-testid="supplier-edit-button">
              <Pencil size={16} />
              Editar
            </Button>
          </Link>
          <Button onClick={() => { setUploadPreset({}); setShowUpload(true); }}>
            <Upload size={16} />
            Subir documento
          </Button>
        </div>
      </header>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Cumplimiento</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="flex items-center gap-6">
            <div>
              <p className="text-3xl font-semibold text-brand-700">{data.compliance_percent}%</p>
              <p className="text-xs uppercase tracking-wide text-neutral-500">global</p>
            </div>
            <div className="flex flex-1 justify-evenly text-sm">
              <Counter label="Vigentes" value={data.counts.valid} tone="text-status-valid" />
              <Counter label="Por vencer" value={data.counts.expiring_soon} tone="text-status-expiring" />
              <Counter label="Vencidos" value={data.counts.expired} tone="text-status-expired" />
              <Counter label="Faltantes" value={data.counts.missing} tone="text-status-missing" />
            </div>
          </div>
        </CardBody>
      </Card>

      {compliance.isLoading ? (
        <p className="mb-6 text-sm text-neutral-500">Cargando cuadrícula…</p>
      ) : bothEmpty ? (
        <div className="mb-6 rounded border border-dashed border-neutral-300 bg-neutral-50 p-8 text-center text-sm text-neutral-600">
          Este proveedor no tiene requisitos de documentación configurados.{" "}
          <Link to="/settings/catalogs/supplier-types" className="text-brand-500 hover:underline">
            Configura el tipo de proveedor en Catálogos.
          </Link>
        </div>
      ) : complianceData ? (
        <>
          <section className="mb-6">
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
                Cumplimiento {year}
              </h2>
            </div>
            <ComplianceGrid
              data={complianceData}
              onUploadClick={handleUploadClick}
              onViewerClose={() => {
                qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
                qc.invalidateQueries({ queryKey: ["supplier-compliance", supplierId] });
              }}
            />
          </section>

          {complianceData.one_time_requirements.length > 0 && (
            <OneTimeRequirements
              items={complianceData.one_time_requirements}
              onDocumentClick={handleDocumentClick}
              onUploadClick={handleUploadClick}
            />
          )}
        </>
      ) : (
        <p className="mb-6 text-sm text-status-expired">No se pudo cargar la cuadrícula.</p>
      )}

      {showUpload && (
        <UploadDialog
          supplierId={supplierId}
          initialDocTypeId={uploadPreset.document_type_id}
          initialCoverage={uploadPreset.coverage_period_start}
          onClose={handleUploadClose}
        />
      )}
    </div>
  );
}

function Counter({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div>
      <p className={`text-xl font-semibold ${tone}`}>{value}</p>
      <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
    </div>
  );
}
