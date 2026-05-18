import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Plus, X } from "lucide-react";

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import { PeriodicitySelect, periodicityLabel } from "@/components/catalogs/PeriodicitySelect";
import { ApiError } from "@/lib/api";
import {
  documentTypesApi,
  supplierTypesApi,
  type Periodicity,
  type RequirementItem,
} from "@/lib/api/index";

export function SupplierTypeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const supplierTypeId = Number(id);
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-type", supplierTypeId],
    queryFn: () => supplierTypesApi.detail(supplierTypeId),
    enabled: !Number.isNaN(supplierTypeId),
  });

  const retire = useMutation({
    mutationFn: ({ reqId, etag }: { reqId: number; etag: string }) =>
      supplierTypesApi.retireRequirement(reqId, etag),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-type", supplierTypeId] }),
  });

  const updateReq = useMutation({
    mutationFn: ({ reqId, etag, override }: { reqId: number; etag: string; override: Periodicity | null }) =>
      supplierTypesApi.updateRequirement(reqId, etag, { periodicity_override: override }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-type", supplierTypeId] }),
  });

  if (isLoading) return <p className="p-8 text-sm text-neutral-500">Cargando…</p>;
  if (!data) return <p className="p-8 text-sm text-status-expired">No encontrado</p>;

  const isSystem = data.origin === "system";
  const reqs = (data.requirements ?? []).filter((r) => r.status === "active");

  return (
    <div className="space-y-6">
      <div>
        <Link to=".." className="text-sm text-brand-500 hover:underline">
          ← Volver a tipos de proveedor
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>{data.name}</CardTitle>
              {data.description && (
                <p className="mt-1 text-sm text-neutral-600">{data.description}</p>
              )}
            </div>
            <Badge tone={isSystem ? "info" : "neutral"}>
              {isSystem ? "Sistema" : "Personalizado"}
            </Badge>
          </div>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-3 gap-6 text-sm">
            <Metric label="Proveedores asociados" value={data.supplier_count} />
            <Metric label="Requisitos activos" value={data.requirement_count} />
            <Metric
              label="Estado"
              value={data.status === "active" ? "Activo" : "Archivado"}
            />
          </div>
        </CardBody>
      </Card>

      <section>
        <header className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Documentos requeridos
          </h2>
          <Button size="sm" onClick={() => setShowAdd(true)}>
            <Plus size={16} />
            Agregar requisito
          </Button>
        </header>

        {reqs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-8 text-center">
            <p className="text-sm text-neutral-600">
              Sin requisitos definidos. Agrega los documentos que un proveedor de este tipo debe presentar.
            </p>
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Tipo de documento</TH>
                <TH>Periodicidad base</TH>
                <TH>Override</TH>
                <TH>Efectiva</TH>
                <TH className="text-right">Acciones</TH>
              </TR>
            </THead>
            <TBody>
              {reqs.map((r) => (
                <RequirementRow
                  key={r.id}
                  req={r}
                  onChangeOverride={(override) =>
                    updateReq.mutate({ reqId: r.id, etag: r.updated_at, override })
                  }
                  onRetire={() => retire.mutate({ reqId: r.id, etag: r.updated_at })}
                />
              ))}
            </TBody>
          </Table>
        )}
      </section>

      {showAdd && (
        <AddRequirementDialog
          supplierTypeId={supplierTypeId}
          excludeIds={new Set(reqs.map((r) => r.document_type.id))}
          onClose={() => setShowAdd(false)}
        />
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-brand-700">{value}</p>
    </div>
  );
}

function RequirementRow({
  req,
  onChangeOverride,
  onRetire,
}: {
  req: RequirementItem;
  onChangeOverride: (override: Periodicity | null) => void;
  onRetire: () => void;
}) {
  return (
    <TR>
      <TD>
        <p className="font-medium text-brand-700">{req.document_type.name}</p>
        <Badge tone={req.document_type.origin === "canonical" ? "info" : "neutral"} className="mt-1">
          {req.document_type.origin === "canonical" ? "Canónico" : "Personalizado"}
        </Badge>
      </TD>
      <TD>{periodicityLabel(req.document_type.periodicity)}</TD>
      <TD>
        <PeriodicitySelect
          value={req.periodicity_override}
          onChange={onChangeOverride}
          includeInherit
          inheritLabel="Heredar"
        />
      </TD>
      <TD>
        <Badge tone="info">{periodicityLabel(req.periodicity_effective)}</Badge>
      </TD>
      <TD className="text-right">
        <Button size="sm" variant="ghost" onClick={onRetire}>
          <X size={14} />
          Retirar
        </Button>
      </TD>
    </TR>
  );
}

function AddRequirementDialog({
  supplierTypeId,
  excludeIds,
  onClose,
}: {
  supplierTypeId: number;
  excludeIds: Set<number>;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [docTypeId, setDocTypeId] = useState<number | null>(null);
  const [override, setOverride] = useState<Periodicity | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.list(false),
  });

  const add = useMutation({
    mutationFn: () =>
      supplierTypesApi.addRequirement(supplierTypeId, {
        document_type_id: docTypeId!,
        periodicity_override: override,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-type", supplierTypeId] });
      onClose();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "already_exists") {
        setError("Ese requisito ya está definido para este tipo.");
      } else if (e instanceof ApiError && e.code === "doc_type_inactive") {
        setError("El tipo de documento está desactivado; reactívalo primero.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Error inesperado");
      }
    },
  });

  const available = (data?.items ?? []).filter((t) => t.active && !excludeIds.has(t.id));

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Agregar requisito</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <div>
            <label className="text-sm font-medium text-brand-700">Tipo de documento</label>
            <select
              className="mt-1.5 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
              value={docTypeId ?? ""}
              onChange={(e) => setDocTypeId(Number(e.target.value) || null)}
              required
            >
              <option value="">Selecciona…</option>
              {available.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({periodicityLabel(t.periodicity)})
                </option>
              ))}
            </select>
            {available.length === 0 && (
              <p className="mt-1 text-xs text-neutral-500">
                No quedan tipos de documento activos para asociar.
              </p>
            )}
          </div>
          <div>
            <label className="text-sm font-medium text-brand-700">
              Periodicidad (opcional override)
            </label>
            <PeriodicitySelect
              value={override}
              onChange={setOverride}
              includeInherit
              inheritLabel="Heredar del tipo de documento"
              className="mt-1.5 w-full"
            />
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={add.isPending || !docTypeId} onClick={() => add.mutate()}>
              {add.isPending ? "Agregando…" : "Agregar"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
