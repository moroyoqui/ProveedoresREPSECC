import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";

import { suppliersApi } from "@/lib/api/index";
import { Badge, Button, Table, TBody, TD, TH, THead, TR } from "@/components/ui";

export function SuppliersListPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => suppliersApi.list({ status: "active" }),
  });

  return (
    <div className="mx-auto max-w-6xl p-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-brand-700">Proveedores</h1>
          <p className="text-sm text-neutral-600">
            Registra y gestiona el cumplimiento REPSE de tus proveedores.
          </p>
        </div>
        <Link to="/suppliers/new">
          <Button>
            <Plus size={16} />
            Nuevo proveedor
          </Button>
        </Link>
      </header>

      {isLoading && <p className="text-sm text-neutral-500">Cargando…</p>}
      {error && <p className="text-sm text-status-expired">No se pudo cargar el listado.</p>}

      {data && data.items.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-10 text-center">
          <p className="text-sm text-neutral-600">Aún no tienes proveedores.</p>
          <Link to="/suppliers/new" className="mt-3 inline-block">
            <Button>
              <Plus size={16} />
              Registra el primero
            </Button>
          </Link>
        </div>
      )}

      {data && data.items.length > 0 && (
        <Table>
          <THead>
            <TR>
              <TH>Razón social</TH>
              <TH>RFC</TH>
              <TH>Tipo</TH>
              <TH>Cumplimiento</TH>
              <TH>Estado</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((s) => (
              <TR key={s.id}>
                <TD>
                  <Link
                    to={`/suppliers/${s.id}`}
                    className="font-medium text-brand-700 hover:underline"
                  >
                    {s.legal_name}
                  </Link>
                </TD>
                <TD className="font-mono text-xs uppercase">{s.rfc}</TD>
                <TD>{s.supplier_type.name}</TD>
                <TD>
                  <div className="flex items-center gap-3">
                    <span className="font-medium">{s.compliance_percent}%</span>
                    <span className="text-xs text-neutral-500">
                      ✓{s.counts.valid} · ⚠{s.counts.expiring_soon} · ⛔{s.counts.expired} · ?{s.counts.missing}
                    </span>
                  </div>
                </TD>
                <TD>
                  <Badge tone={s.status === "active" ? "info" : "neutral"}>{s.status}</Badge>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
