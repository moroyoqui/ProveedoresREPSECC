import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DestructiveConfirmDialog,
  FormField,
} from "@/components/ui";
import {
  fetchSupplierTypeChangePreview,
  parseTypeChangeError,
  useChangeSupplierType,
  type AffectedDocument,
} from "@/lib/api/suppliers";
import { suppliersApi, supplierTypesApi } from "@/lib/api/index";

/**
 * Edición de un proveedor con flujo destructivo de cambio de tipo (T132 spec 001).
 *
 * Al guardar, si el tipo cambió:
 *  1. Consulta `type-change-preview`.
 *  2. Si `requires_confirmation`, abre `<DestructiveConfirmDialog>` con la
 *     lista de documentos.
 *  3. Tras confirmar, envía `PATCH` con `confirmation_text`.
 *  4. Maneja 409/422 mostrando feedback claro.
 */
export function EditSupplierPage() {
  const { id } = useParams<{ id: string }>();
  const supplierId = Number(id);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const supplierQ = useQuery({
    queryKey: ["supplier", supplierId],
    queryFn: () => suppliersApi.detail(supplierId),
    enabled: Number.isFinite(supplierId),
  });
  const typesQ = useQuery({
    queryKey: ["supplier-types"],
    queryFn: () => supplierTypesApi.list(),
  });

  const [legalName, setLegalName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [supplierTypeId, setSupplierTypeId] = useState<number | null>(null);
  const [originalTypeId, setOriginalTypeId] = useState<number | null>(null);
  const [topError, setTopError] = useState<string | null>(null);
  const [topNotice, setTopNotice] = useState<string | null>(null);
  const [pendingAffected, setPendingAffected] = useState<AffectedDocument[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    if (supplierQ.data) {
      setLegalName(supplierQ.data.legal_name);
      setContactEmail(supplierQ.data.contact_email ?? "");
      setContactPhone(""); // El detalle actual no expone contact_phone; queda vacío.
      setSupplierTypeId(supplierQ.data.supplier_type.id);
      setOriginalTypeId(supplierQ.data.supplier_type.id);
    }
  }, [supplierQ.data]);

  const change = useChangeSupplierType(supplierId, {
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
      navigate(`/suppliers/${supplierId}`);
    },
    onError: (err) => {
      const parsed = parseTypeChangeError(err);
      if (parsed.kind === "confirmation_required") {
        setPendingAffected(parsed.affected_documents);
        setTopError(null);
      } else if (parsed.kind === "invalid_confirmation") {
        setTopError(
          `El texto de confirmación no coincide. Debes escribir "${parsed.expected}".`
        );
      } else {
        setTopError(parsed.message);
      }
    },
  });

  const baseFields = () => ({
    legal_name: legalName || undefined,
    contact_email: contactEmail || undefined,
    contact_phone: contactPhone || undefined,
  });

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTopError(null);
    setTopNotice(null);
    if (supplierTypeId === null) {
      setTopError("Selecciona un tipo de proveedor.");
      return;
    }
    const typeChanged = supplierTypeId !== originalTypeId;
    if (!typeChanged) {
      // No hay cambio destructivo posible — PATCH directo.
      change.mutate({
        supplier_type_id: supplierTypeId,
        ...baseFields(),
      } as never);
      return;
    }
    // El tipo cambió: consultamos preview antes de mostrar el modal.
    setPreviewLoading(true);
    try {
      const preview = await fetchSupplierTypeChangePreview(supplierId, supplierTypeId);
      if (preview.requires_confirmation) {
        setPendingAffected(preview.affected_documents);
      } else {
        change.mutate({
          supplier_type_id: supplierTypeId,
          ...baseFields(),
        } as never);
        setTopNotice("Tipo actualizado. Sin documentos del año en curso afectados.");
      }
    } catch (err) {
      const parsed = parseTypeChangeError(err);
      setTopError(parsed.kind === "other" ? parsed.message : "No se pudo consultar el preview.");
    } finally {
      setPreviewLoading(false);
    }
  }

  function handleConfirmDestructive() {
    if (supplierTypeId === null) return;
    change.mutate({
      supplier_type_id: supplierTypeId,
      confirmation_text: "eliminar",
      ...baseFields(),
    } as never);
  }

  function handleCancelDestructive() {
    setPendingAffected(null);
  }

  if (supplierQ.isLoading) {
    return <p className="p-8 text-sm text-neutral-500">Cargando…</p>;
  }
  if (!supplierQ.data) {
    return <p className="p-8 text-sm text-status-expired">Proveedor no encontrado.</p>;
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <Link
        to={`/suppliers/${supplierId}`}
        className="text-sm text-brand-500 hover:underline"
      >
        ← Volver al detalle
      </Link>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Editar proveedor</CardTitle>
          <p className="mt-1 text-sm text-neutral-600">
            Cambiar el tipo elimina los documentos del año en curso. Otros años se conservan.
          </p>
        </CardHeader>
        <CardBody>
          {topError && (
            <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">
              {topError}
            </p>
          )}
          {topNotice && (
            <p className="mb-4 rounded-md bg-green-50 px-3 py-2 text-sm text-status-valid">
              {topNotice}
            </p>
          )}
          <form className="space-y-4" onSubmit={handleSave}>
            <FormField
              label="Razón social"
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
            />
            <FormField
              label="RFC"
              value={supplierQ.data.rfc}
              disabled
              hint="El RFC no se edita aquí (FR-006 spec 001)."
            />
            <div>
              <label
                className="text-sm font-medium text-brand-700"
                htmlFor="supplier_type_id"
              >
                Tipo de proveedor
              </label>
              <select
                id="supplier_type_id"
                data-testid="supplier-type-select"
                className="mt-1.5 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
                value={supplierTypeId ?? ""}
                onChange={(e) =>
                  setSupplierTypeId(Number(e.target.value) || null)
                }
              >
                {typesQ.data?.items.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <FormField
              type="email"
              label="Correo de contacto"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
            />
            <FormField
              label="Teléfono de contacto"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
            />
            <div className="flex justify-end gap-3 pt-2">
              <Link to={`/suppliers/${supplierId}`}>
                <Button type="button" variant="ghost">
                  Cancelar
                </Button>
              </Link>
              <Button
                type="submit"
                disabled={change.isPending || previewLoading}
                data-testid="supplier-save-button"
              >
                {change.isPending || previewLoading ? "Guardando…" : "Guardar cambios"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {pendingAffected !== null && (
        <DestructiveConfirmDialog
          title="Confirmar cambio destructivo"
          description={
            "Al cambiar el tipo de proveedor se eliminarán permanentemente los " +
            "siguientes documentos cuyo vencimiento cae en el año en curso. " +
            "Los archivos físicos también se borrarán."
          }
          items={pendingAffected.map((d) => ({
            id: d.id,
            primary: d.document_type,
            secondary: [
              d.coverage_period && `Periodo: ${d.coverage_period}`,
              d.due_date_effective && `Vence: ${d.due_date_effective}`,
            ]
              .filter(Boolean)
              .join(" · "),
          }))}
          busy={change.isPending}
          onConfirm={handleConfirmDestructive}
          onCancel={handleCancelDestructive}
        />
      )}
    </div>
  );
}
