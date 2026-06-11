import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus } from "lucide-react";

import { Button, Card, CardBody, CardHeader, CardTitle, FormField, Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { sectorsApi, type SectorItem } from "@/lib/api/sectors";

export function SectorsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data: sectors = [], isLoading } = useQuery({
    queryKey: ["sectors"],
    queryFn: sectorsApi.list,
  });

  const removeMut = useMutation({
    mutationFn: sectorsApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sectors"] }),
  });

  if (isLoading) return <p className="text-sm text-neutral-500">Cargando…</p>;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={16} />
          Nuevo sector
        </Button>
      </div>

      {sectors.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-10 text-center">
          <p className="text-sm text-neutral-600">
            Aún no hay sectores. Crea el primero para comenzar a clasificar proveedores.
          </p>
        </div>
      )}

      {sectors.length > 0 && (
        <Table>
          <THead>
            <TR>
              <TH>Nombre</TH>
              <TH className="text-right">Acciones</TH>
            </TR>
          </THead>
          <TBody>
            {sectors.map((s) => (
              <SectorRow
                key={s.id}
                sector={s}
                onDelete={() => {
                  if (confirm(`¿Eliminar el sector "${s.name}"?`)) {
                    removeMut.mutate(s.id);
                  }
                }}
                onUpdated={() => qc.invalidateQueries({ queryKey: ["sectors"] })}
              />
            ))}
          </TBody>
        </Table>
      )}

      {showCreate && <SectorFormDialog onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function SectorRow({
  sector,
  onDelete,
  onUpdated,
}: {
  sector: SectorItem;
  onDelete: () => void;
  onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);

  return editing ? (
    <SectorEditRow sector={sector} onCancel={() => setEditing(false)} onSaved={() => { setEditing(false); onUpdated(); }} />
  ) : (
    <TR>
      <TD><span className="font-medium text-brand-700">{sector.name}</span></TD>
      <TD className="text-right">
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
            Editar
          </Button>
          <Button size="sm" variant="secondary" onClick={onDelete}>
            Eliminar
          </Button>
        </div>
      </TD>
    </TR>
  );
}

function SectorEditRow({
  sector,
  onCancel,
  onSaved,
}: {
  sector: SectorItem;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState(sector.name);
  const [error, setError] = useState<string | null>(null);

  const updateMut = useMutation({
    mutationFn: () => sectorsApi.update(sector.id, { name }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sectors"] });
      onSaved();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "sector_name_taken") {
        setError("Ya existe un sector con ese nombre.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Error inesperado");
      }
    },
  });

  return (
    <TR>
      <TD>
        <div className="flex flex-col gap-1">
          <input
            className="h-9 w-full rounded-md border border-neutral-300 px-3 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && updateMut.mutate()}
            autoFocus
          />
          {error && <p className="text-xs text-status-expired">{error}</p>}
        </div>
      </TD>
      <TD className="text-right">
        <div className="flex justify-end gap-2">
          <Button size="sm" disabled={updateMut.isPending || !name.trim()} onClick={() => updateMut.mutate()}>
            {updateMut.isPending ? "Guardando…" : "Guardar"}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        </div>
      </TD>
    </TR>
  );
}

function SectorFormDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: () => sectorsApi.create({ name }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sectors"] });
      onClose();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "sector_name_taken") {
        setError("Ya existe un sector con ese nombre.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Error inesperado");
      }
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Nuevo sector</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <FormField
            label="Nombre del sector"
            placeholder="Construcción"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>Cancelar</Button>
            <Button disabled={createMut.isPending || !name.trim()} onClick={() => createMut.mutate()}>
              {createMut.isPending ? "Creando…" : "Crear"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
