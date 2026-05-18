import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { suppliersApi, supplierTypesApi } from "@/lib/api/index";
import { Button, Card, CardBody, CardHeader, CardTitle, FormField } from "@/components/ui";
import { ApiError } from "@/lib/api";

const schema = z.object({
  legal_name: z.string().min(3, "Mínimo 3 caracteres").max(255),
  rfc: z.string().regex(/^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$/i, "RFC inválido"),
  supplier_type_id: z.coerce.number().optional(),
  contact_name: z.string().max(255).optional(),
  contact_email: z.string().email("Correo inválido").optional().or(z.literal("")),
  contact_phone: z.string().max(32).optional(),
});

export function NewSupplierPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [topError, setTopError] = useState<string | null>(null);

  const { data: typesData } = useQuery({
    queryKey: ["supplier-types"],
    queryFn: () => supplierTypesApi.list(),
  });

  const createMut = useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      navigate(`/suppliers/${created.id}`);
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError) {
        if (e.code === "rfc_exists") {
          setErrors({ rfc: "Ya existe un proveedor con este RFC" });
          return;
        }
        setTopError(e.message);
      } else {
        setTopError("Error inesperado");
      }
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const parsed = schema.safeParse({
      legal_name: fd.get("legal_name"),
      rfc: (fd.get("rfc") as string)?.toUpperCase(),
      supplier_type_id: fd.get("supplier_type_id") || undefined,
      contact_name: fd.get("contact_name"),
      contact_email: fd.get("contact_email"),
      contact_phone: fd.get("contact_phone"),
    });
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const path = issue.path.join(".");
        fieldErrors[path] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    setTopError(null);
    const payload = {
      ...parsed.data,
      contact_email: parsed.data.contact_email || undefined,
    };
    createMut.mutate(payload);
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <Link to="/suppliers" className="text-sm text-brand-500 hover:underline">
        ← Volver a proveedores
      </Link>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Nuevo proveedor</CardTitle>
          <p className="mt-1 text-sm text-neutral-600">
            Si no eliges tipo, se asigna "Sin clasificar" (exige el catálogo completo).
          </p>
        </CardHeader>
        <CardBody>
          {topError && (
            <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">
              {topError}
            </p>
          )}
          <form className="space-y-4" onSubmit={handleSubmit}>
            <FormField
              name="legal_name"
              label="Razón social"
              placeholder="Servicios Industriales del Norte SA de CV"
              error={errors.legal_name}
              required
            />
            <FormField
              name="rfc"
              label="RFC"
              placeholder="ABC123456X1Z"
              error={errors.rfc}
              required
              maxLength={13}
            />
            <div>
              <label className="text-sm font-medium text-brand-700" htmlFor="supplier_type_id">
                Tipo de proveedor
              </label>
              <select
                name="supplier_type_id"
                id="supplier_type_id"
                defaultValue=""
                className="mt-1.5 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
              >
                <option value="">Sin clasificar (default)</option>
                {typesData?.items.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <FormField name="contact_name" label="Contacto" placeholder="Juan Pérez" />
            <FormField name="contact_email" type="email" label="Correo de contacto" error={errors.contact_email} />
            <FormField name="contact_phone" label="Teléfono" placeholder="+52 81 1234 5678" />
            <div className="flex justify-end gap-3 pt-2">
              <Link to="/suppliers">
                <Button type="button" variant="ghost">
                  Cancelar
                </Button>
              </Link>
              <Button type="submit" disabled={createMut.isPending}>
                {createMut.isPending ? "Guardando…" : "Crear proveedor"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
