import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Button, Card, CardBody, CardHeader, CardTitle, FormField } from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";
import { authApi } from "@/lib/api/index";

/**
 * Acceso dedicado del portal del proveedor (spec 013, US4 / FR-012).
 * Solo correo y contraseña, con audience "portal": una credencial que no sea
 * de proveedor recibe el mismo mensaje genérico que credenciales inválidas
 * (FR-013); la orientación a la puerta administrativa es el enlace estático.
 */
export function PortalLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sesión de proveedor ya activa → directo a Consulta.
  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me(),
    retry: false,
    staleTime: 60_000,
  });
  if (me?.role === "supplier") {
    return <Navigate to="/portal/consulta" replace />;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch("/auth/login", {
        method: "POST",
        json: { email, password, audience: "portal" },
      });
      navigate("/portal/consulta", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.code === "invalid_credentials") {
        setError("Correo o contraseña incorrectos.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Error inesperado.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-full items-center justify-center bg-emerald-50">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <p className="text-xs uppercase tracking-widest text-emerald-600">REPSE</p>
          <CardTitle>Portal del Proveedor</CardTitle>
          <p className="mt-1 text-sm text-neutral-500">
            Consulta y entrega tu documentación de cumplimiento.
          </p>
        </CardHeader>
        <CardBody className="space-y-4">
          <form className="space-y-3" onSubmit={handleSubmit}>
            <FormField
              label="Correo"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="proveedor@empresa.mx"
            />
            <FormField
              label="Contraseña"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Entrando…" : "Entrar al portal"}
            </Button>
          </form>

          <p className="text-center text-xs text-neutral-500">
            ¿Personal administrativo?{" "}
            <Link to="/login" className="font-medium text-brand-700 hover:underline">
              Entra por aquí
            </Link>
          </p>
        </CardBody>
      </Card>
    </main>
  );
}
