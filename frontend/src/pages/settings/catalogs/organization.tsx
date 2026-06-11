import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";

import { organizationsApi, type OrganizationPatch } from "@/lib/api/index";
import { Button, Card, CardBody, CardHeader, CardTitle, FormField } from "@/components/ui";

const MX_TIMEZONES = [
  { value: "America/Mexico_City", label: "Centro — CDMX, Jalisco, Veracruz (CST/CDT)" },
  { value: "America/Monterrey", label: "Norte — Nuevo León, Tamaulipas (CST/CDT)" },
  { value: "America/Chihuahua", label: "Mountain — Chihuahua, Sinaloa, Durango (MST/MDT)" },
  { value: "America/Hermosillo", label: "Pacífico sin DST — Sonora (MST)" },
  { value: "America/Tijuana", label: "Pacífico — Baja California (PST/PDT)" },
  { value: "America/Cancun", label: "Sureste — Quintana Roo (EST)" },
];

export function OrganizationSettingsPage() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["organization"],
    queryFn: () => organizationsApi.get(),
  });

  const [form, setForm] = useState<OrganizationPatch>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) {
      setForm({
        legal_name: data.legal_name,
        contact_email: data.contact_email,
        expiring_soon_threshold_days: data.expiring_soon_threshold_days,
        timezone: data.timezone,
      });
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => organizationsApi.patch(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["organization"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate();
  }

  if (isLoading) return <p className="text-sm text-neutral-500">Cargando…</p>;

  return (
    <div className="max-w-xl">
      <Card>
        <CardHeader>
          <CardTitle>Datos de la organización</CardTitle>
        </CardHeader>
        <CardBody>
          {mutation.isError && (
            <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              Error al guardar. Verifica los datos e intenta de nuevo.
            </p>
          )}
          {saved && (
            <p className="mb-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
              Cambios guardados correctamente.
            </p>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-brand-700">RFC</label>
              <p className="mt-1 font-mono text-sm text-neutral-500">{data?.rfc}</p>
              <p className="text-xs text-neutral-400">El RFC no puede modificarse.</p>
            </div>

            <FormField
              label="Razón social"
              value={form.legal_name ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, legal_name: e.target.value }))}
              required
              minLength={2}
              maxLength={255}
            />

            <FormField
              label="Correo de contacto"
              type="email"
              value={form.contact_email ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
              required
            />

            <div>
              <label className="text-sm font-medium text-brand-700" htmlFor="timezone">
                Zona horaria
              </label>
              <select
                id="timezone"
                className="mt-1.5 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm"
                value={form.timezone ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
              >
                {MX_TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {tz.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium text-brand-700" htmlFor="threshold">
                Días de aviso antes del vencimiento
              </label>
              <p className="mb-1.5 text-xs text-neutral-500">
                Los documentos que vencen dentro de este plazo se marcan como "Por vencer". Rango: 1–90 días.
              </p>
              <input
                id="threshold"
                type="number"
                min={1}
                max={90}
                className="h-10 w-32 rounded-md border border-neutral-300 bg-white px-3 text-sm"
                value={form.expiring_soon_threshold_days ?? 15}
                onChange={(e) =>
                  setForm((f) => ({ ...f, expiring_soon_threshold_days: Number(e.target.value) }))
                }
                required
              />
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Guardando…" : "Guardar cambios"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
