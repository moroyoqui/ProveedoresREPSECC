import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, FormField, Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { supplierTypesApi, type SupplierTypeItem } from "@/lib/api/index";

export function SupplierTypesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-types", "all"],
    queryFn: () => supplierTypesApi.list("all"),
  });

  const archive = useMutation({
    mutationFn: (id: number) => supplierTypesApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-types"] }),
  });
  const restore = useMutation({
    mutationFn: (id: number) => supplierTypesApi.restore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-types"] }),
  });

  if (isLoading) return <p className="text-sm text-neutral-500">Cargando…</p>;
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={16} />
          Nuevo tipo
        </Button>
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Nombre</TH>
            <TH>Origen</TH>
            <TH>Estado</TH>
            <TH>Proveedores</TH>
            <TH>Requisitos</TH>
            <TH className="text-right">Acciones</TH>
          </TR>
        </THead>
        <TBody>
          {items.map((st) => (
            <SupplierTypeRow
              key={st.id}
              st={st}
              onArchive={() => archive.mutate(st.id)}
              onRestore={() => restore.mutate(st.id)}
            />
          ))}
        </TBody>
      </Table>

      {showCreate && <CreateSupplierTypeDialog onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function SupplierTypeRow({
  st,
  onArchive,
  onRestore,
}: {
  st: SupplierTypeItem;
  onArchive: () => void;
  onRestore: () => void;
}) {
  const isSystem = st.origin === "system";
  return (
    <TR>
      <TD>
        <Link
          to={`./${st.id}`}
          className="font-medium text-brand-700 hover:underline"
        >
          {st.name}
        </Link>
        {st.description && <p className="text-xs text-neutral-500 line-clamp-2">{st.description}</p>}
      </TD>
      <TD>
        <Badge tone={isSystem ? "info" : "neutral"}>{isSystem ? "Sistema" : "Personalizado"}</Badge>
      </TD>
      <TD>
        <Badge tone={st.status === "active" ? "valid" : "missing"}>
          {st.status === "active" ? "Activo" : "Archivado"}
        </Badge>
      </TD>
      <TD>{st.supplier_count}</TD>
      <TD>{st.requirement_count}</TD>
      <TD className="text-right">
        {isSystem ? (
          <span className="text-xs text-neutral-400">inmutable</span>
        ) : st.status === "active" ? (
          <Button size="sm" variant="secondary" onClick={onArchive}>
            Archivar
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={onRestore}>
            Restaurar
          </Button>
        )}
      </TD>
    </TR>
  );
}

function CreateSupplierTypeDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      supplierTypesApi.create({ name, description: description || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-types"] });
      onClose();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "name_exists") {
        setError("Ya existe un tipo con ese nombre.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Error inesperado");
      }
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Nuevo tipo de proveedor</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <FormField
            label="Nombre"
            placeholder="Ej: Construcción, Servicios profesionales, Transporte..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <FormField
            label="Descripción (opcional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={create.isPending || !name} onClick={() => create.mutate()}>
              {create.isPending ? "Creando…" : "Crear"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
