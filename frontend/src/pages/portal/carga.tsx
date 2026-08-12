import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { FileStack, Upload } from "lucide-react";

import { Badge } from "@/components/ui";
import { portalApi } from "@/lib/api/portal";
import { PortalDocumentViewerModal } from "@/components/portal/PortalDocumentViewerModal";
import {
  CURRENT_YEAR,
  YEAR_OPTIONS,
  statusLabel,
  statusTone,
  uploadableItems,
  type UploadableItem,
} from "./shared";

/**
 * Pantalla de CARGA del portal del proveedor (spec 013, US1).
 * Lista únicamente las celdas elegibles para carga (Faltante / Pendiente /
 * Vencido — reglas 009 sin cambios, FR-003/FR-007) con el flujo de subida y
 * envío a validación. Lee ?type=&period= para preseleccionar (US2, FR-004).
 */
export function PortalCargaPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [active, setActive] = useState<UploadableItem | null>(null);
  const [preselected, setPreselected] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["portal-compliance", year],
    queryFn: () => portalApi.getCompliance(year),
  });

  const items = data ? uploadableItems(data) : [];

  // Preselección por contexto desde Consulta (FR-004); los parámetros que no
  // correspondan a una celda elegible se ignoran.
  useEffect(() => {
    if (preselected || !data) return;
    setPreselected(true);
    const type = searchParams.get("type");
    const period = searchParams.get("period");
    if (!type) return;
    const match = uploadableItems(data).find(
      (it) =>
        it.document_type_id === Number(type) &&
        (it.coverage_period_start ?? "") === (period ?? "")
    );
    if (match) setActive(match);
    setSearchParams({}, { replace: true });
  }, [data, preselected, searchParams, setSearchParams]);

  function handleInvalidate() {
    // FR-011: al volver a Consulta el estado actualizado es visible sin recarga.
    qc.invalidateQueries({ queryKey: ["portal-compliance"] });
  }

  if (isLoading) return <p className="p-8 text-sm text-neutral-500">Cargando…</p>;
  if (isError || !data)
    return <p className="p-8 text-sm text-red-600">No fue posible cargar la información. Intenta de nuevo.</p>;

  return (
    <>
    <div className="mx-auto max-w-4xl p-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-neutral-500">Carga de documentos</p>
          <h1 className="text-2xl font-semibold text-brand-700">{data.supplier.legal_name}</h1>
          <p className="mt-1 text-sm text-neutral-600">
            Selecciona un documento pendiente para subir archivos y enviarlos a validación.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-neutral-600">Año:</label>
          <select
            className="h-9 rounded-md border border-neutral-300 bg-white px-3 text-sm"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </header>

      {items.length === 0 ? (
        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-4 text-sm text-green-800">
          <FileStack size={18} className="shrink-0 text-green-600" />
          Toda tu documentación de {year} está al corriente: no hay nada pendiente de cargar.
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm shadow-sm"
            >
              <span className="text-neutral-800">
                <span className="font-medium">{item.documentTypeName}</span>
                <span className="ml-2 text-xs text-neutral-500">{item.periodLabel}</span>
              </span>
              <span className="flex items-center gap-3">
                <Badge tone={statusTone(item.status)}>{statusLabel(item.status)}</Badge>
                <button
                  type="button"
                  onClick={() => setActive(item)}
                  className="flex items-center gap-1.5 rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
                >
                  <Upload size={13} />
                  Cargar archivos
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>

    {/* Diálogo de carga + envío a validación (flujo 009 sin cambios) */}
    {active && data && (
      <PortalDocumentViewerModal
        supplierId={data.supplier.id}
        documentTypeId={active.document_type_id}
        documentTypeName={active.documentTypeName}
        coveragePeriodStart={active.coverage_period_start}
        canAddDocuments
        canSubmit
        uploadFn={(file) =>
          portalApi
            .upload(file, active.document_type_id, active.coverage_period_start ?? undefined)
            .then(() => {})
        }
        onSubmitted={() => {
          handleInvalidate();
          setActive(null);
        }}
        onClose={() => {
          handleInvalidate();
          setActive(null);
        }}
      />
    )}
    </>
  );
}
