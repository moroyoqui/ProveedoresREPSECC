import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { Pencil, Upload } from "lucide-react";

import { suppliersApi } from "@/lib/api/index";
import { Button, Card, CardBody, CardHeader, CardTitle } from "@/components/ui";
import { UploadDialog } from "@/components/documents/UploadDialog";
import { ComplianceGrid } from "@/components/suppliers/ComplianceGrid";

export function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>();
  const supplierId = Number(id);
  const [showUpload, setShowUpload] = useState(false);
  const year = new Date().getFullYear();

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

  if (isLoading) return <p className="p-8 text-sm text-neutral-500">Cargando…</p>;
  if (!data) return <p className="p-8 text-sm text-status-expired">No encontrado</p>;

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
        </div>
        <div className="flex gap-2">
          <Link to={`/suppliers/${data.id}/edit`}>
            <Button variant="secondary" data-testid="supplier-edit-button">
              <Pencil size={16} />
              Editar
            </Button>
          </Link>
          <Button onClick={() => setShowUpload(true)}>
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
            <div className="grid grid-cols-4 gap-4 text-sm">
              <Counter label="Vigentes" value={data.counts.valid} tone="text-status-valid" />
              <Counter label="Por vencer" value={data.counts.expiring_soon} tone="text-status-expiring" />
              <Counter label="Vencidos" value={data.counts.expired} tone="text-status-expired" />
              <Counter label="Faltantes" value={data.counts.missing} tone="text-status-missing" />
            </div>
          </div>
        </CardBody>
      </Card>

      <section className="mb-6">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Cumplimiento {year}
          </h2>
        </div>
        {compliance.isLoading ? (
          <p className="text-sm text-neutral-500">Cargando cuadrícula…</p>
        ) : compliance.data ? (
          <ComplianceGrid data={compliance.data} />
        ) : (
          <p className="text-sm text-status-expired">No se pudo cargar la cuadrícula.</p>
        )}
      </section>

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
