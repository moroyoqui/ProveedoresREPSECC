import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Pencil, Plus } from "lucide-react";

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, FormField, Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import { PeriodicitySelect, periodicityLabel } from "@/components/catalogs/PeriodicitySelect";
import { ApiError } from "@/lib/api";
import { documentTypesApi, type DocumentTypeItem, type Periodicity } from "@/lib/api/index";

export function DocumentTypesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editingDt, setEditingDt] = useState<DocumentTypeItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["document-types", "all"],
    queryFn: () => documentTypesApi.list(true),
  });

  const toggleCanonical = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      documentTypesApi.toggleCanonical(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document-types"] }),
  });

  const archiveCustom = useMutation({
    mutationFn: (id: number) => documentTypesApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document-types"] }),
  });

  const restoreCustom = useMutation({
    mutationFn: (id: number) => documentTypesApi.restore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document-types"] }),
  });

  if (isLoading) return <p className="text-sm text-neutral-500">Cargando…</p>;

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={16} />
          Tipo personalizado
        </Button>
      </div>

      <Table>
        <THead>
          <TR>
            <TH>Nombre</TH>
            <TH>Periodicidad</TH>
            <TH>Origen</TH>
            <TH>Estado</TH>
            <TH className="text-right">Acciones</TH>
          </TR>
        </THead>
        <TBody>
          {items.map((dt) => (
            <DocumentTypeRow
              key={dt.id}
              dt={dt}
              onToggle={(active) => toggleCanonical.mutate({ id: dt.id, active })}
              onArchive={() => archiveCustom.mutate(dt.id)}
              onRestore={() => restoreCustom.mutate(dt.id)}
              onEdit={() => setEditingDt(dt)}
            />
          ))}
        </TBody>
      </Table>

      {showCreate && <CreateDocumentTypeDialog onClose={() => setShowCreate(false)} />}
      {editingDt && (
        <EditDocumentTypeDialog dt={editingDt} onClose={() => setEditingDt(null)} />
      )}
    </div>
  );
}

function DocumentTypeRow({
  dt,
  onToggle,
  onArchive,
  onRestore,
  onEdit,
}: {
  dt: DocumentTypeItem;
  onToggle: (active: boolean) => void;
  onArchive: () => void;
  onRestore: () => void;
  onEdit: () => void;
}) {
  return (
    <TR>
      <TD>
        <p className="font-medium text-brand-700">{dt.name}</p>
        {dt.description && <p className="text-xs text-neutral-500">{dt.description}</p>}
      </TD>
      <TD>{periodicityLabel(dt.periodicity)}</TD>
      <TD>
        <Badge tone={dt.origin === "canonical" ? "info" : "neutral"}>
          {dt.origin === "canonical" ? "Canónico" : "Personalizado"}
        </Badge>
      </TD>
      <TD>
        <Badge tone={dt.active ? "valid" : "missing"}>{dt.active ? "Activo" : "Inactivo"}</Badge>
      </TD>
      <TD className="text-right">
        <div className="flex items-center justify-end gap-2">
          {dt.origin === "custom" && (
            <Button size="sm" variant="ghost" onClick={onEdit} title="Editar">
              <Pencil size={14} />
            </Button>
          )}
          {dt.origin === "canonical" ? (
            <Button size="sm" variant="secondary" onClick={() => onToggle(!dt.active)}>
              {dt.active ? "Desactivar" : "Activar"}
            </Button>
          ) : dt.active ? (
            <Button size="sm" variant="secondary" onClick={onArchive}>
              Archivar
            </Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={onRestore}>
              Restaurar
            </Button>
          )}
        </div>
      </TD>
    </TR>
  );
}

function EditDocumentTypeDialog({
  dt,
  onClose,
}: {
  dt: DocumentTypeItem;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState(dt.name);
  const [description, setDescription] = useState(dt.description ?? "");
  const [periodicity, setPeriodicity] = useState<Periodicity | null>(dt.periodicity as Periodicity);
  const [error, setError] = useState<string | null>(null);

  const update = useMutation({
    mutationFn: () =>
      documentTypesApi.update(dt.id, dt.updated_at, {
        name: name.trim() !== dt.name ? name.trim() : undefined,
        description: description || undefined,
        periodicity: periodicity ?? undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document-types"] });
      onClose();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "name_exists") {
        setError("Ya existe un tipo con ese nombre en tu organización.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Error inesperado");
      }
    },
  });

  const hasChanges =
    name.trim() !== dt.name ||
    (description || undefined) !== (dt.description ?? undefined) ||
    periodicity !== dt.periodicity;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Editar tipo de documento</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <FormField label="Nombre" value={name} onChange={(e) => setName(e.target.value)} required />
          <FormField
            label="Descripción (opcional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div>
            <label className="text-sm font-medium text-brand-700">Periodicidad</label>
            <PeriodicitySelect value={periodicity} onChange={setPeriodicity} className="mt-1.5 w-full" />
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              disabled={update.isPending || !name || !periodicity || !hasChanges}
              onClick={() => update.mutate()}
            >
              {update.isPending ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function CreateDocumentTypeDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [periodicity, setPeriodicity] = useState<Periodicity | null>("monthly");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      documentTypesApi.create({
        name,
        description: description || undefined,
        periodicity: (periodicity ?? "monthly") as Periodicity,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document-types"] });
      onClose();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "name_exists") {
        setError("Ya existe un tipo con ese nombre en tu organización.");
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
          <CardTitle>Nuevo tipo de documento personalizado</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <FormField label="Nombre" value={name} onChange={(e) => setName(e.target.value)} required />
          <FormField
            label="Descripción (opcional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div>
            <label className="text-sm font-medium text-brand-700">Periodicidad</label>
            <PeriodicitySelect value={periodicity} onChange={setPeriodicity} className="mt-1.5 w-full" />
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              disabled={create.isPending || !name || !periodicity}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Creando…" : "Crear"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
