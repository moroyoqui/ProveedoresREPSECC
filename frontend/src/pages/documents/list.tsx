import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Button, Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import { ComplianceBadge } from "@/components/documents/ComplianceBadge";
import { DocumentDetailDrawer } from "@/components/documents/DocumentDetailDrawer";
import { DocumentFiltersBar } from "@/components/documents/DocumentFiltersBar";
import { VerifiedBadge } from "@/components/documents/VerifiedBadge";
import { VerifyDialog } from "@/components/documents/VerifyDialog";
import { useDocumentsList, type DocumentListFilters, type DocumentListItem } from "@/lib/api/documents";
import { documentsApi } from "@/lib/api/index";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

function formatPeriod(start: string | null): string {
  if (!start) return "—";
  const d = new Date(start + "T12:00:00");
  return d.toLocaleDateString("es-MX", { month: "short", year: "numeric" });
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function filtersFromSearchParams(sp: URLSearchParams): DocumentListFilters {
  const out: DocumentListFilters = {};
  if (sp.has("q")) out.q = sp.get("q")!;
  if (sp.has("verified")) out.verified = sp.get("verified") === "true";
  if (sp.has("status")) out.status = sp.get("status") as DocumentListFilters["status"];
  if (sp.has("supplier_id")) out.supplier_id = Number(sp.get("supplier_id"));
  if (sp.has("document_type_id")) out.document_type_id = Number(sp.get("document_type_id"));
  return out;
}

export function DocumentsListPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<DocumentListFilters>(() =>
    filtersFromSearchParams(searchParams)
  );
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [verifyTarget, setVerifyTarget] = useState<DocumentListItem | null>(null);
  const [unverifyError, setUnverifyError] = useState<string | null>(null);

  const { data, isLoading, isError } = useDocumentsList(filters);
  const qc = useQueryClient();

  const unverify = useMutation({
    mutationFn: (id: number) => documentsApi.unverify(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents-list"] });
      setUnverifyError(null);
    },
    onError: (e: unknown) => {
      setUnverifyError(e instanceof ApiError ? e.message : "Error al quitar verificación.");
    },
  });

  const items = data?.items ?? [];
  const selectedDoc = selectedDocId != null ? (items.find((d) => d.id === selectedDocId) ?? null) : null;

  function handleRowClick(doc: DocumentListItem) {
    setSelectedDocId(doc.id);
  }

  function handleDrawerClose() {
    setSelectedDocId(null);
  }

  function handleVerifySuccess() {
    qc.invalidateQueries({ queryKey: ["documents-list"] });
    setVerifyTarget(null);
  }

  function handleUnverifySuccess() {
    qc.invalidateQueries({ queryKey: ["documents-list"] });
  }

  return (
    <div className="mx-auto max-w-7xl p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-brand-700">Documentos</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Consulta y verifica los archivos cargados por cada proveedor. Haz clic en una fila para ver el detalle.
        </p>
      </header>

      <DocumentFiltersBar filters={filters} onChange={setFilters} />

      {unverifyError && (
        <p className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {unverifyError}
        </p>
      )}

      {isLoading && (
        <p className="py-12 text-center text-sm text-neutral-500">Cargando documentos…</p>
      )}

      {isError && (
        <p className="py-12 text-center text-sm text-red-600">
          Error al cargar documentos. Intenta nuevamente.
        </p>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <div className="py-12 text-center text-sm text-neutral-500">
          Sin resultados. Ajusta los filtros para ver documentos.
        </div>
      )}

      {!isLoading && !isError && items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-neutral-200">
          <Table>
            <THead>
              <TR>
                <TH>Proveedor</TH>
                <TH>Tipo de documento</TH>
                <TH>Periodo</TH>
                <TH>Vencimiento</TH>
                <TH>Estado</TH>
                <TH>Verificación</TH>
                <TH>Agregado</TH>
                <TH className="text-right">Acciones</TH>
              </TR>
            </THead>
            <TBody>
              {items.map((doc) => (
                <TR
                  key={doc.id}
                  className="cursor-pointer hover:bg-neutral-50 transition-colors"
                  onClick={() => handleRowClick(doc)}
                >
                  <TD className="font-medium">{doc.supplier?.legal_name ?? "—"}</TD>
                  <TD>
                    <span className="text-sm text-neutral-700">
                      {doc.document_type?.name ?? `Tipo #${doc.document_type_id}`}
                    </span>
                  </TD>
                  <TD>{formatPeriod(doc.coverage_period_start)}</TD>
                  <TD className="text-sm text-neutral-600">{formatDate(doc.due_date_effective)}</TD>
                  <TD>
                    <ComplianceBadge status={doc.status} />
                  </TD>
                  <TD>
                    <VerifiedBadge document={doc} />
                  </TD>
                  <TD className="text-sm text-neutral-500">
                    {formatDate(doc.audit.added.at)}
                  </TD>
                  <TD
                    className="text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedDocId(doc.id);
                        }}
                      >
                        Ver
                      </Button>
                      {!doc.verified && (user?.role === "admin" || user?.role === "manager") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            setVerifyTarget(doc);
                          }}
                        >
                          Verificar
                        </Button>
                      )}
                      {doc.verified && user?.role === "admin" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={unverify.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            unverify.mutate(doc.id);
                          }}
                        >
                          Quitar verificación
                        </Button>
                      )}
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </div>
      )}

      {data?.has_more && (
        <p className="mt-4 text-center text-sm text-neutral-500">
          Hay más documentos. Ajusta los filtros para acotar la búsqueda.
        </p>
      )}

      {selectedDoc && (
        <DocumentDetailDrawer
          document={selectedDoc}
          onClose={handleDrawerClose}
          onVerify={() => setVerifyTarget(selectedDoc)}
          onUnverifySuccess={handleUnverifySuccess}
        />
      )}

      {verifyTarget && (
        <VerifyDialog
          document={verifyTarget}
          supplierId={verifyTarget.supplier_id}
          onClose={handleVerifySuccess}
        />
      )}
    </div>
  );
}
