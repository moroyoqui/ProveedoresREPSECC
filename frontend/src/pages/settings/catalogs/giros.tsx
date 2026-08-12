import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Plus } from "lucide-react";

import { Button, Card, CardBody, CardHeader, CardTitle, FormField, Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { girosApi, type GiroItem } from "@/lib/api/giros";
import { sectorsApi } from "@/lib/api/sectors";

export function GirosPage() {
  const qc = useQueryClient();
  const [filterSectorId, setFilterSectorId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: sectors = [] } = useQuery({
    queryKey: ["sectors"],
    queryFn: sectorsApi.list,
  });

  const { data: giros = [], isLoading } = useQuery({
    queryKey: ["giros", filterSectorId],
    queryFn: () => girosApi.list(filterSectorId ?? undefined),
  });

  const removeMut = useMutation({
    mutationFn: girosApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["giros"] }),
  });

  if (isLoading) return <p className="text-sm text-neutral-500">Cargando…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-neutral-700">Filtrar por sector:</label>
          <select
            className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm"
            value={filterSectorId ?? ""}
            onChange={(e) => setFilterSectorId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Todos los sectores</option>
            {sectors.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={16} />
          Nuevo giro
        </Button>
      </div>

      {sectors.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-10 text-center">
          <p className="text-sm text-neutral-600">
            Primero debes crear al menos un sector antes de agregar giros.
          </p>
        </div>
      )}

      {sectors.length > 0 && giros.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-10 text-center">
          <p className="text-sm text-neutral-600">
            {filterSectorId ? "No hay giros en este sector." : "Aún no hay giros. Crea el primero."}
          </p>
        </div>
      )}

      {giros.length > 0 && (
        <Table>
          <THead>
            <TR>
              <TH>Giro</TH>
              <TH>Sector</TH>
              <TH className="text-right">Acciones</TH>
            </TR>
          </THead>
          <TBody>
            {giros.map((g) => (
              <GiroRow
                key={g.id}
                giro={g}
                sectors={sectors}
                onDelete={() => {
                  if (confirm(`¿Eliminar el giro "${g.name}"?`)) {
                    removeMut.mutate(g.id);
                  }
                }}
                onUpdated={() => qc.invalidateQueries({ queryKey: ["giros"] })}
              />
            ))}
          </TBody>
        </Table>
      )}

      {showCreate && (
        <GiroFormDialog
          sectors={sectors}
          defaultSectorId={filterSectorId ?? undefined}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}

function GiroRow({
  giro,
  sectors,
  onDelete,
  onUpdated,
}: {
  giro: GiroItem;
  sectors: { id: number; name: string }[];
  onDelete: () => void;
  onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);

  return editing ? (
    <GiroEditRow
      giro={giro}
      sectors={sectors}
      onCancel={() => setEditing(false)}
      onSaved={() => { setEditing(false); onUpdated(); }}
    />
  ) : (
    <TR>
      <TD><span className="font-medium text-brand-700">{giro.name}</span></TD>
      <TD className="text-sm text-neutral-600">{giro.sector_name}</TD>
      <TD className="text-right">
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>Editar</Button>
          <Button size="sm" variant="secondary" onClick={onDelete}>Eliminar</Button>
        </div>
      </TD>
    </TR>
  );
}

function GiroEditRow({
  giro,
  sectors,
  onCancel,
  onSaved,
}: {
  giro: GiroItem;
  sectors: { id: number; name: string }[];
  onCancel: () => void;
  onSaved: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState(giro.name);
  const [sectorId, setSectorId] = useState(giro.sector_id);
  const [error, setError] = useState<string | null>(null);

  const updateMut = useMutation({
    mutationFn: () => girosApi.update(giro.id, { name, sector_id: sectorId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["giros"] });
      onSaved();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "giro_name_taken") {
        setError("Ya existe un giro con ese nombre en este sector.");
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
            autoFocus
          />
          {error && <p className="text-xs text-status-expired">{error}</p>}
        </div>
      </TD>
      <TD>
        <select
          className="h-9 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
          value={sectorId}
          onChange={(e) => setSectorId(Number(e.target.value))}
        >
          {sectors.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </TD>
      <TD className="text-right">
        <div className="flex justify-end gap-2">
          <Button size="sm" disabled={updateMut.isPending || !name.trim()} onClick={() => updateMut.mutate()}>
            {updateMut.isPending ? "Guardando…" : "Guardar"}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel}>Cancelar</Button>
        </div>
      </TD>
    </TR>
  );
}

function GiroFormDialog({
  sectors,
  defaultSectorId,
  onClose,
}: {
  sectors: { id: number; name: string }[];
  defaultSectorId?: number;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [sectorId, setSectorId] = useState<number>(defaultSectorId ?? sectors[0]?.id ?? 0);
  const [error, setError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: () => girosApi.create({ sector_id: sectorId, name }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["giros"] });
      onClose();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "giro_name_taken") {
        setError("Ya existe un giro con ese nombre en este sector.");
      } else if (e instanceof ApiError && e.code === "not_found") {
        setError("El sector seleccionado no existe.");
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
          <CardTitle>Nuevo giro</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <div>
            <label className="text-sm font-medium text-brand-700">Sector</label>
            <select
              className="mt-1.5 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
              value={sectorId}
              onChange={(e) => setSectorId(Number(e.target.value))}
            >
              {sectors.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <FormField
            label="Nombre del giro"
            placeholder="Plomería"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>Cancelar</Button>
            <Button disabled={createMut.isPending || !name.trim() || !sectorId} onClick={() => createMut.mutate()}>
              {createMut.isPending ? "Creando…" : "Crear"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
