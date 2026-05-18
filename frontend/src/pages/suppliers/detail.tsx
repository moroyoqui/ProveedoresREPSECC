import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { Upload } from "lucide-react";

import { suppliersApi } from "@/lib/api/index";
import { Button, Card, CardBody, CardHeader, CardTitle, Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import { StatusBadge } from "@/components/documents/StatusBadge";
import { UploadDialog } from "@/components/documents/UploadDialog";

export function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>();
  const supplierId = Number(id);
  const [showUpload, setShowUpload] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["supplier", supplierId],
    queryFn: () => suppliersApi.detail(supplierId),
    enabled: !Number.isNaN(supplierId),
  });

  if (isLoading) return <p className="p-8 text-sm text-neutral-500">Cargando…</p>;
  if (!data) return <p className="p-8 text-sm text-status-expired">No encontrado</p>;

  return (
    <div className="mx-auto max-w-5xl p-8">
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
        </div>
        <Button onClick={() => setShowUpload(true)}>
          <Upload size={16} />
          Subir documento
        </Button>
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
            <div className="grid grid-cols-4 gap-4 text-sm">
              <Counter label="Vigentes" value={data.counts.valid} tone="text-status-valid" />
              <Counter label="Por vencer" value={data.counts.expiring_soon} tone="text-status-expiring" />
              <Counter label="Vencidos" value={data.counts.expired} tone="text-status-expired" />
              <Counter label="Faltantes" value={data.counts.missing} tone="text-status-missing" />
            </div>
          </div>
        </CardBody>
      </Card>

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
        Documentos requeridos
      </h2>
      <Table>
        <THead>
          <TR>
            <TH>Tipo</TH>
            <TH>Periodo</TH>
            <TH>Vencimiento</TH>
            <TH>Estado</TH>
            <TH>Verificado</TH>
          </TR>
        </THead>
        <TBody>
          {data.documents_by_type.map((row) => (
            <TR key={row.document_type.id}>
              <TD>{row.document_type.name}</TD>
              <TD className="text-neutral-600">
                {row.latest?.coverage_period_start ?? "—"}
              </TD>
              <TD>{row.latest?.due_date_effective ?? "—"}</TD>
              <TD>
                <StatusBadge status={row.latest?.status || row.status_override || "missing"} />
              </TD>
              <TD>{row.latest?.verified ? "✓" : "—"}</TD>
            </TR>
          ))}
        </TBody>
      </Table>

      {showUpload && (
        <UploadDialog supplierId={supplierId} onClose={() => setShowUpload(false)} />
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
